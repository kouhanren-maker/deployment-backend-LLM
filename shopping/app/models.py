from django.db import models


# ========== 1. User ==========
class User(models.Model):
    email = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=128)
    role = models.CharField(max_length=64)
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users"


# ========== 2. Administor（关联 User） ==========
class Administor(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, db_column="user_id")
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "administors"


# ========== 3. Customer（关联 User） ==========
class Customer(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, db_column="user_id")
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "customers"

# ========== Merchant（关联 User） ==========
class Merchant(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, db_column="user_id")
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "merchants"


# ========== 4. Attribute ==========
class Attribute(models.Model):
    code = models.CharField(max_length=100)   # 图中无 UNIQUE（去掉）
    value = models.CharField(max_length=100)
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "attributes"
        constraints = [
            models.UniqueConstraint(fields=["code", "value"], name="uk_code_value")
        ]


# ========== 5. Product（关联 Attribute） ==========
class Product(models.Model):
    attribute = models.ForeignKey(
        Attribute, on_delete=models.SET_NULL, null=True, db_column="attribute_id"
    )
    description = models.CharField(max_length=100, unique=True)
    type = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=100, unique=True)
    brand = models.CharField(max_length=100, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    source = models.CharField(max_length=1000)
    value_datetime = models.DateTimeField(auto_now_add=True)
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "products"


# ========== 6. Product_User_portrait（关联 Product） ==========
class ProductUserPortrait(models.Model):
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, db_column="product_id")
    age_avg = models.IntegerField(null=True, blank=True)
    gender = models.CharField(max_length=64)
    region = models.CharField(max_length=64)
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "product_user_portraits"


# ========== 7. Merchant_hot_product ==========
class MerchantHotProduct(models.Model):
    name = models.CharField(max_length=50)
    description = models.CharField(max_length=200)
    view_count = models.IntegerField()
    purchase_count = models.IntegerField()
    season = models.CharField(max_length=64)
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "merchant_hot_products"


# ========== 8. User_Dialogue（关联 User） ==========
class UserDialogue(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, db_column="user_id")
    question = models.TextField()
    answer = models.TextField()
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_dialogues"


# ========== 9. Customer_Preference（关联 Customer / Product / Attribute） ==========
class CustomerPreference(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, db_column="customer_id")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, db_column="product_id")
    preference = models.TextField()
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "customer_preferences"
