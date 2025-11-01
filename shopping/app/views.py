import os
import requests
from django.db import transaction, IntegrityError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from .models import UserDialogue, Product, Attribute
from .models import Customer, Product, CustomerPreference
from .serializers import RegisterSerializer, LoginSerializer
from .auth_utils import create_jwt_for_user, authenticate_credentials
from .models import User, MerchantHotProduct
from .auth_decorators import jwt_required, admin_required, merchant_required
from django.http import JsonResponse

from .models import (
    User, UserDialogue,
    Merchant, MerchantHotProduct, ProductUserPortrait
)
AI_AGENT_URL = os.getenv("AI_AGENT_URL", "http://127.0.0.1:9000/agent")

from pathlib import Path
import json




# -------------------------------------------------------------------------------

# Register
@api_view(["POST"])
@permission_classes([AllowAny])
def register_view(request):
    """
    POST /api/register
    Body: { "email": "...", "password": "...", "role": "customer" }
    """
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        return Response({"id": user.id, "email": user.email, "role": user.role}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Login
@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    """
    POST /api/login
    Body: { "email": "...", "password": "..." }
    Returns: { "token": "jwt..." }
    """
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    email = serializer.validated_data["email"]
    password = serializer.validated_data["password"]

    user = authenticate_credentials(email, password)
    if user is None:
        return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

    token = create_jwt_for_user(user)
    return Response({"token": token, "user": {"id": user.id, "email": user.email, "role": user.role}})

# Admin endpoint
@api_view(["GET"])
@admin_required
def list_users_view(request):
    """
    GET api/admin/list_users
    Headers: 
            Key: Authorization
            Value: Bearer <token>
    """
    users = User.objects.all().values("id", "email", "role", "create_time")
    return JsonResponse({"users": list(users)}, safe=False)


# -------------------------------------------------------------------------------

# Merchant function: season hot products report
@api_view(["POST"])
@merchant_required
def generate_merchant_report(request, user_id ): 

    """
    POST api/merchant/report/<user_id>/
    Body:
        {
            "query": "Show me top products for Autumn 2025"
        }

    This endpoint:
    1. Logs the merchant query into UserDialogue.
    2. Loads a mock AI response from mock/merchant_query.json.
    3. Saves hot product info into MerchantHotProduct table.
    4. Returns a seasonal report.
    """

    # check if user a merchant (path variable)
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"error": f"User {user_id} not found"}, status=status.HTTP_404_NOT_FOUND)
    if user.role.lower() != "merchant":
        return Response({"error": "Merchant privileges required"}, status=status.HTTP_403_FORBIDDEN)
    

    # 1. extract query
    query = (request.data.get("query") or "").strip()
    if not query:
        return Response({"detail": "query is required"}, status=status.HTTP_400_BAD_REQUEST)

    print(query)

    # 2. create dialogue record
    dialogue = UserDialogue.objects.create(
        user_id=user_id,
        question=query,
        answer="",           
    )

    # 3. mock AI response with 3-hottest products in the season
    local_path = Path(__file__).resolve().parent / "mock" / "merchant_query.json"
    try:
        with open(local_path, "r", encoding="utf-8") as f:
            ai_data = json.load(f)
    except FileNotFoundError:
        return Response({"detail": f"data.json not found: {local_path}"}, status=status.HTTP_400_BAD_REQUEST)
    except json.JSONDecodeError as e:
        return Response({"detail": f"data.json invalid JSON: {e}"}, status=status.HTTP_400_BAD_REQUEST)

    print(ai_data)

    # 4. parse AI response
    year = ai_data.get("year", "")
    season = ai_data.get("season", "")
    products_payload = ai_data.get("products", [])
    answer = ai_data.get("answer", "")

    if not isinstance(products_payload, list):
        return Response({"detail": "Invalid products format: products must be a list"},
                        status=status.HTTP_400_BAD_REQUEST)

    # 5. Save into DB (atomic transaction)
    saved_products = []
    with transaction.atomic():
        for p in products_payload:
            prod = MerchantHotProduct.objects.create(
                name=p.get(("name") or "")[:50],
                description=p.get(("description") or "")[:200],
                view_count=int(p.get("view_count", 0)),
                purchase_count=int(p.get("purchase_count", 0)),
                season=f"{year} {season}",
            )

            saved_products.append({
                "id": prod.id,
                "name": p.get("name"),
                "description": p.get("description"),
                "view_count": prod.view_count,
                "purchase_count": prod.purchase_count,
                "season": prod.season,
            })

        # Update dialogue answer
        dialogue.answer = answer
        dialogue.save(update_fields=["answer", "update_time"])

    # 6. return response
    return Response(
        {
            "data": {
                "year": year,
                "season": season,
                "products": saved_products,
                "answer": answer,
            },
            "response": {
                "ok": True,
                "saved_count": len(saved_products),
            }
        },
        status=status.HTTP_200_OK,
    )


# -------------------------------------------------------------------------------

@api_view(["POST"])
@permission_classes([AllowAny])
def process_customer_data(request, user_id: int):
    """
    1️⃣ 根据 user_id 从数据库中查找历史对话作为 history
    2️⃣ 发送 {question, history} 给 ai-agent:9000/
    3️⃣ 解析返回的 {product, answer}
    4️⃣ 将 products 和 answer 落库
    """

    question = (request.data.get("question") or "").strip()
    if not question:
        return Response({"detail": "question is required"}, status=status.HTTP_400_BAD_REQUEST)

    # Step 1️⃣: 查询历史问答记录
    history_qas = list(
        UserDialogue.objects.filter(user_id=user_id)
        .order_by("create_time")
        .values("question", "answer")
    )
    history = [{"question": q["question"], "answer": q["answer"]} for q in history_qas]
    print(history)
    dialogue = UserDialogue.objects.create(
        user_id=user_id,
        question=question,
        answer="",           # 先空着，成功/失败后统一回填
    )

    # Step 2️⃣: 请求 AI-Agent
    try:
        ai_response = requests.post(
            AI_AGENT_URL,
            json={"text": question, "history": history},
            timeout=30,
        )
        ai_response.raise_for_status()
    except requests.RequestException as e:
        return Response({"detail": f"AI-Agent error: {e}"}, status=status.HTTP_502_BAD_GATEWAY)

    try:
        ai_data = ai_response.json()
    except ValueError:
        return Response({"detail": "AI-Agent returned invalid JSON"}, status=status.HTTP_502_BAD_GATEWAY)

    # --- use local app/data.json when requested ---

    # —— 直接读本地 data.json —— #





    #
    # from pathlib import Path
    # import json
    #
    # local_path = Path(__file__).resolve().parent / "data.json"  # 与 views.py 同级
    # try:
    #     with open(local_path, "r", encoding="utf-8") as fh:
    #         ai_data = json.load(fh)
    # except FileNotFoundError:
    #     return Response({"detail": f"data.json not found: {local_path}"}, status=status.HTTP_400_BAD_REQUEST)
    # except json.JSONDecodeError as e:
    #     return Response({"detail": f"data.json invalid JSON: {e}"}, status=status.HTTP_400_BAD_REQUEST)


    

#     local_path = Path(__file__).resolve().parent / "mock" / "data.json"  # 与 views.py 同级
#     try:
#         with open(local_path, "r", encoding="utf-8") as fh:
#             ai_data = json.load(fh)
#     except FileNotFoundError:
#         return Response({"detail": f"data.json not found: {local_path}"}, status=status.HTTP_400_BAD_REQUEST)
#     except json.JSONDecodeError as e:
#         return Response({"detail": f"data.json invalid JSON: {e}"}, status=status.HTTP_400_BAD_REQUEST)



    print(ai_data)

    # 4) 解析
    products_payload = ai_data.get("product") or ai_data.get("products") or []
    answer = ai_data.get("answer", "")
    if not isinstance(products_payload, list):
        return Response({"detail": "Invalid product format: product must be a list"},
                        status=status.HTTP_400_BAD_REQUEST)

    # 5) 落库（按 ER 图：Product 只能挂一个 attribute，所以只挑一个）
    def pick_one_attr(attrs):
        if not attrs:
            return None
        if isinstance(attrs, dict):
            k, v = next(iter(attrs.items()))
            return str(k), str(v)
        if isinstance(attrs, list) and attrs and isinstance(attrs[0], dict) and len(attrs[0]) == 1:
            k, v = next(iter(attrs[0].items()))
            return str(k), str(v)
        return None

    product_rows = []  # 用于回传给前端的简版列表
    attr_created = 0
    prod_created = 0

    with transaction.atomic():
        for p in products_payload:
            if not isinstance(p, dict):
                continue

            # 5.1 选一个属性并 upsert Attribute
            chosen_attr_obj = None
            chosen = pick_one_attr(p.get("attributes"))
            if chosen:
                code, value = chosen
                chosen_attr_obj, was_created = Attribute.objects.get_or_create(code=code, value=value)
                if was_created:
                    attr_created += 1

            # 5.2 upsert Product（以 source 作为主键；其余字段更新）
            source = (p.get("source") or "")[:1000]
            if not source:
                # 没有 source 容易撞唯一约束，这里直接跳过
                continue

            try:
                prod, created = Product.objects.update_or_create(
                    source=source,
                    defaults=dict(
                        attribute=chosen_attr_obj,
                        description=(p.get("description") or "")[:100],
                        type=(p.get("type") or "")[:100],
                        name=(p.get("name") or "")[:100],
                        brand=(p.get("brand") or "")[:100],
                        price=p.get("price"),
                    ),
                )
            except IntegrityError:
                # 命中其它唯一键冲突则跳过该条
                continue

            if created:
                prod_created += 1

            product_rows.append({
                "id": prod.id,
                "name": prod.name,
                "source": prod.source,
            })

        # 5.3 回填本次对话的 answer
        dialogue.answer = str(answer)[:2000]
        dialogue.save(update_fields=["answer", "update_time"])

    # 6) 返回给前端（按你给的结构）
    return Response(
        {
            "data": {
                "product": product_rows,  # 只返回 id / name / source
                "answer": answer
            },
            "response": {
                "ok": True,
                "stats": {
                    "attributes_created": attr_created,
                    "products_created": prod_created,
                    "total_products": len(product_rows),
                },
                "history_size": len(history)
            }
        },
        status=status.HTTP_200_OK,
    )










def _resolve_customer(user_id: int) -> Customer:
    """
    兼容两种传参：
    1) user_id 直接是 Customer.id -> 直接取 pk
    2) user_id 是 User.id -> 用 Customer.user_id 去匹配
    """
    # 先当作 Customer 主键
    cust = Customer.objects.filter(id=user_id).first()
    if cust:
        return cust
    # 再当作 User 主键映射
    cust = Customer.objects.filter(user_id=user_id).first()
    if cust:
        return cust
    # 两种方式都没有则 404
    raise Customer.DoesNotExist


@api_view(["GET"])
@permission_classes([AllowAny])
def user_preference(request, user_id: int, product_id: int):
    """
    GET /customer/<user_id>/product/<product_id>/
    作用：把 (customer_id, product_id) 记录到 customer_preference 表
    返回：
    {
      "ok": true,
      "data": {"id": 12, "customer_id": 3, "product_id": 7, "status": "created|exists"}
    }
    """
    # 1) 解析并校验实体
    try:
        customer = _resolve_customer(user_id)
    except Customer.DoesNotExist:
        return Response({"detail": f"customer not found for id={user_id}"}, status=status.HTTP_404_NOT_FOUND)

    product = get_object_or_404(Product, pk=product_id)

    # 2) 幂等写入（存在则不重复插入）
    pref, created = CustomerPreference.objects.get_or_create(
        customer=customer,
        product=product,
        defaults={},  # 时间戳自动填
    )

    # 若已存在，顺手更新时间戳（便于你看最近一次选择）
    if not created:
        pref.update_time = timezone.now()
        pref.save(update_fields=["update_time"])

    return Response(
        {
            "ok": True,
            "data": {
                "id": pref.id,
                "customer_id": customer.id,
                "product_id": product.id,
                "status": "created" if created else "exists",
            },
        },
        status=status.HTTP_200_OK,
    )




@api_view(["POST"])
@permission_classes([AllowAny])
def user_portrait(request, user_id: int):
    """
    接收商家问题 -> 转发给 AI-Agent -> 记录问答 -> 落库商家热销数据
    """
    question = (request.data.get("question") or "").strip()
    if not question:
        return Response({"detail": "question is required"}, status=status.HTTP_400_BAD_REQUEST)

    user = get_object_or_404(User, id=user_id)

    # 1️⃣ 获取用户历史问答记录
    # history_qas = UserDialogue.objects.filter(user=user).values("question", "answer")
    # history = [{"question": q["question"], "answer": q["answer"]} for q in history_qas]

    # payload = {"question": question, "history": history}
    payload = {"question": question}

    try:
        # 2️⃣ 调用 AI-Agent 接口
        ai_response = requests.post(AI_AGENT_URL, json=payload, timeout=60)
        ai_response.raise_for_status()
        data = ai_response.json()  # 返回的数据
    except Exception as e:
        return Response({"detail": f"AI-Agent request failed: {e}"}, status=status.HTTP_502_BAD_GATEWAY)

    # 假设返回格式如下：
    # {
    #   "merchant_hot_products": [
    #       {
    #           "merchant_id": 1,
    #           "name": "Nike Air Force 1",
    #           "view_count": 50,
    #           "purchase_count": 20,
    #           "season": "Spring"
    #       }, ...
    #   ],
    #   "product_user_portraits": [
    #       {
    #           "merchant_hot_product_id": 1,
    #           "age_avg": 25,
    #           "gender": "Male",
    #           "region": "Sydney"
    #       }, ...
    #   ],
    #   "answer": "Some analytical report ..."
    # }

    try:
        with transaction.atomic():
            # 3️⃣ 插入当前问答记录
            UserDialogue.objects.create(
                user=user,
                question=question,
                answer=data.get("answer", "")
            )

            # 4️⃣ 保存 merchant_hot_products
            mhp_list = data.get("merchant_hot_products", [])
            for item in mhp_list:
                MerchantHotProduct.objects.create(
                    merchant_id=item.get("merchant_id"),
                    name=item.get("name"),
                    view_count=item.get("view_count", 0),
                    purchase_count=item.get("purchase_count", 0),
                    season=item.get("season", "")
                )

            # 5️⃣ 保存 product_user_portraits
            pup_list = data.get("product_user_portraits", [])
            for item in pup_list:
                ProductUserPortrait.objects.create(
                    merchant_hot_product_id=item.get("merchant_hot_product_id"),
                    age_avg=item.get("age_avg"),
                    gender=item.get("gender", ""),
                    region=item.get("region", "")
                )

    except IntegrityError as e:
        return Response({"detail": f"Database error: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # 6️⃣ 返回结果
    return Response({
        "data": data,
        "response": "Merchant data processed successfully"
    }, status=status.HTTP_200_OK)