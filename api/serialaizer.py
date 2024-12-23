from rest_framework import serializers
from .models import CustomUser, UserProfile, Wallet, Transaction
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password


# Serializer for user registration
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password', 'password_confirm']

    def validate(self, data):
        """Validate that passwords match"""
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        # Check if username or email already exists
        if CustomUser.objects.filter(username=data['username']).exists():
            raise serializers.ValidationError({"username": "Username already exists."})
        if CustomUser.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({"email": "Email already exists."})
        return data

    def create(self, validated_data):
        """Hash the password before saving the user"""
        validated_data.pop('password_confirm')  # Remove password_confirm
        validated_data['password'] = make_password(validated_data['password'])  # Hash the password
        user = CustomUser.objects.create(**validated_data)
        return user


# Serializer for user login
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, style={'input_type': 'password'})

    def validate(self, data):
        """Authenticate the user"""
        user = authenticate(username=data['username'], password=data['password'])
        if not user:
            raise serializers.ValidationError({"detail": "Invalid username or password"})
        return user


# Serializer for UserProfile
class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ('id', 'salary')


# Serializer for Wallet
class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ('id', 'balance')


# Combined Serializer for CustomUser with Profile and Wallet
class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer()
    wallet = WalletSerializer()

    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'email', 'profile', 'wallet')


# Serializer for Transaction
class TransactionSerializer(serializers.ModelSerializer):
    wallet = serializers.PrimaryKeyRelatedField(queryset=Wallet.objects.all())

    class Meta:
        model = Transaction
        fields = ('id', 'wallet', 'amount', 'transaction_type', 'category', 'description', 'date')

    def validate(self, data):
        """Validate transaction before saving"""
        wallet = data['wallet']
        amount = data['amount']
        transaction_type = data['transaction_type']

        if transaction_type == 'expense' and wallet.balance < amount:
            raise serializers.ValidationError({"detail": "Insufficient balance in the wallet for this expense."})

        return data

    def create(self, validated_data):
        """Create a transaction and adjust wallet balance"""
        wallet = validated_data['wallet']
        transaction_type = validated_data['transaction_type']
        amount = validated_data['amount']

        # Create transaction and update balance
        transaction = Transaction.objects.create(**validated_data)
        if transaction_type == 'expense':
            wallet.update_balance(-amount)
        elif transaction_type == 'income':
            wallet.update_balance(amount)
        return transaction
