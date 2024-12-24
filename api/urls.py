from django.urls import path
from api.views import *

urlpatterns = [
    # Wallet URLs
    path('wallets/', WalletListView.as_view(), name='wallet-list'),
    path('wallets/<int:pk>/', WalletDetailView.as_view(), name='wallet-detail'),
    # Transaction URLs
    path('transactions/', TransactionListView.as_view(), name='transaction-list'),
    path('transactions/<int:pk>/', TransactionDetailView.as_view(), name='transaction-detail'),

    # UserProfile URLs
    path('userprofile/', UserProfileCreateView.as_view(), name='userprofile-create'),
    path('userprofile/list/', UserProfileListView.as_view(), name='userprofile-list'),

    # Report URL
    path('reports/', ReportView.as_view(), name='report')
]
