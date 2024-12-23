from django.contrib import admin
from .models import CustomUser, UserProfile, Wallet, Transaction


# Inline for UserProfile
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    readonly_fields = ('salary',)
    verbose_name_plural = 'User Profiles'


# Inline for Wallet
class WalletInline(admin.StackedInline):
    model = Wallet
    can_delete = False
    readonly_fields = ('balance',)
    verbose_name_plural = 'Wallets'


# CustomUser Admin
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'date_joined', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    list_filter = ('is_active', 'is_staff', 'date_joined')
    ordering = ('date_joined',)
    inlines = [UserProfileInline, WalletInline]


# UserProfile Admin
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_email', 'salary')
    search_fields = ('user__username', 'user__email')
    list_filter = ('user__is_staff',)
    ordering = ('user',)

    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'User Email'


# Wallet Admin
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'get_email')
    search_fields = ('user__username', 'user__email')
    list_filter = ('user__is_active',)
    ordering = ('user',)
    readonly_fields = ('balance',)

    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'User Email'


# Transaction Admin
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('wallet', 'get_user', 'amount', 'transaction_type', 'category', 'date')
    list_filter = ('transaction_type', 'category', 'date')
    search_fields = ('wallet__user__username', 'wallet__user__email')
    date_hierarchy = 'date'  # Филтр барои сана
    ordering = ('-date',)
    readonly_fields = ('wallet', 'amount', 'transaction_type', 'category', 'date', 'description')

    def get_user(self, obj):
        return obj.wallet.user.username
    get_user.short_description = 'User'


# Сабти моделҳо дар admin
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(Wallet, WalletAdmin)
admin.site.register(Transaction, TransactionAdmin)
