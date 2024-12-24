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
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        if CustomUser.objects.filter(username=data['username']).exists():
            raise serializers.ValidationError({"username": "Username already exists."})
        if CustomUser.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({"email": "Email already exists."})
        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm') 
        validated_data['password'] = make_password(validated_data['password'])  
        user = CustomUser.objects.create(**validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, style={'input_type': 'password'})

    def validate(self, data):
        user = authenticate(username=data['username'], password=data['password'])
        if not user:
            raise serializers.ValidationError({"detail": "Invalid username or password"})
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ('id', 'salary')


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ('id', 'balance')


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer()
    wallet = WalletSerializer()

    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'email', 'profile', 'wallet')

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ('id', 'amount', 'transaction_type', 'category', 'description', 'date')  # `wallet` хориҷ карда шуд

    def validate(self, data):
        """Валидасия барои санҷидани бақияи кофӣ барои хароҷот."""
        user = self.context['request'].user
        wallet = Wallet.objects.get(user=user)
        amount = data['amount']
        transaction_type = data['transaction_type']

        if transaction_type == 'expense' and wallet.balance < amount:
            raise serializers.ValidationError({"detail": "Insufficient balance in the wallet for this expense."})

        return data

    def create(self, validated_data):
        """Создани амалиёт ва навсозии бақияи ҳамён."""
        transaction_type = validated_data['transaction_type']
        amount = validated_data['amount']

        # `wallet`-ро аз validated_data хориҷ мекунем
        wallet = Wallet.objects.get(user=self.context['request'].user)
        validated_data.pop('wallet', None)  # `wallet`-ро хориҷ кунед, агар вуҷуд дошта бошад

        transaction = Transaction.objects.create(wallet=wallet, **validated_data)

        # Навсозии бақияи ҳамён
        if transaction_type == 'income':
            wallet.update_balance(amount)
        elif transaction_type == 'expense':
            wallet.update_balance(-amount)

        return transaction




