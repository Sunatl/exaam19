from django.forms import ValidationError
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from api.models import Wallet, Transaction, UserProfile
from api.serialaizer import WalletSerializer, TransactionSerializer, UserProfileSerializer
from django.db.models import Sum, Q
from rest_framework.pagination import PageNumberPagination
from datetime import datetime

# Pagination
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

# Wallet Views
class WalletListView(generics.ListCreateAPIView):
    serializer_class = WalletSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        """ Фақат маълумотҳои корбарро нишон медиҳем. """
        return Wallet.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """Создани хазинаи корбар."""
        serializer.save(user=self.request.user)


class WalletDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = WalletSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Фақат маълумоти Wallet-и корбарро нишон медиҳем."""
        return Wallet.objects.filter(user=self.request.user)

# Transaction Views
class TransactionListView(generics.ListCreateAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        """Фақат амалиётҳои корбарро нишон медиҳем."""
        queryset = Transaction.objects.filter(wallet__user=self.request.user)

        # Filtering by month, year, week
        month = self.request.query_params.get('month')
        year = self.request.query_params.get('year')
        week = self.request.query_params.get('week')

        if month:
            queryset = queryset.filter(date__month=int(month))
        if year:
            queryset = queryset.filter(date__year=int(year))
        if week:
            queryset = queryset.filter(date__week=int(week))

        return queryset

    def perform_create(self, serializer):
        """Сохтани амалиёт ва ёрӣ бо дигаргунии ҳамён."""
        transaction = serializer.save()
        transaction.wallet.update_balance(
            transaction.amount if transaction.transaction_type == "income" else -transaction.amount
        )


class TransactionDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Фақат амалиётҳои корбарро нишон медиҳем."""
        return Transaction.objects.filter(wallet__user=self.request.user)

# UserProfile Views
class UserProfileCreateView(generics.CreateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        # Check if the user already has a profile
        existing_profile = UserProfile.objects.get(user=self.request.user)

        if existing_profile:
            return Response({"detail": "User profile already exists."}, status=status.HTTP_400_BAD_REQUEST)

        serializer.save(user=self.request.user)


class UserProfileListView(generics.ListAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserProfile.objects.filter(user=self.request.user)

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Q, Count
from rest_framework.exceptions import ValidationError
from .models import Transaction, Wallet
from .serialaizer import TransactionSerializer
from django_filters import rest_framework as filters
from rest_framework.pagination import PageNumberPagination

# Filter for transactions
class TransactionFilter(filters.FilterSet):
    start_date = filters.DateFilter(field_name='date', lookup_expr='gte')
    end_date = filters.DateFilter(field_name='date', lookup_expr='lte')
    day = filters.NumberFilter(field_name='date__day')
    month = filters.NumberFilter(field_name='date__month')
    year = filters.NumberFilter(field_name='date__year')
    week = filters.NumberFilter(field_name='date__week')

    class Meta:
        model = Transaction
        fields = ['start_date', 'end_date', 'day', 'month', 'year', 'week']

# Pagination class for the API
class CustomPagination(PageNumberPagination):
    page_size = 10  # Set the number of items per page
    page_size_query_param = 'page_size'
    max_page_size = 100  # Maximum items per page


class ReportView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = TransactionFilter
    serializer_class = TransactionSerializer
    pagination_class = CustomPagination  # Set the pagination class

    def get_queryset(self):
        """Retrieve transactions for the authenticated user's wallet."""
        user_wallet = Wallet.objects.filter(user=self.request.user).first()
        if not user_wallet:
            return Transaction.objects.none()
        return Transaction.objects.filter(wallet=user_wallet)

    def calculate_totals(self, queryset):
        """Calculate total income and expense for the queryset."""
        return queryset.aggregate(
            total_income=Sum('amount', filter=Q(transaction_type='income')),
            total_expense=Sum('amount', filter=Q(transaction_type='expense'))
        )

    def count_transactions(self, queryset, transaction_type):
        """Count the number of transactions of a specific type."""
        return queryset.filter(transaction_type=transaction_type).count()

    def get_user_wallet(self):
        """Retrieve the authenticated user's wallet."""
        return Wallet.objects.filter(user=self.request.user).first()

    def validate_date_range(self, start_date, end_date):
        """Ensure the start_date is not after the end_date."""
        if start_date and end_date and start_date > end_date:
            raise ValidationError("Start date cannot be after end date.")

    def get_pagination_info(self, page):
        """Get pagination data."""
        # Only calculate pagination if we have a paginated response (page is not a list)
        if isinstance(page, list):
            return {}
        return {
            'current_page': page.number,
            'total_pages': page.paginator.num_pages,
            'total_items': page.paginator.count
        }

    def count_by_category(self, queryset):
        """Count transactions by categories."""
        return queryset.values('category').annotate(count=Count('id'))

    def get_date_range_summary(self, queryset, start_date, end_date):
        """Provide a summary for transactions in a date range."""
        if start_date and end_date:
            return queryset.filter(date__gte=start_date, date__lte=end_date).aggregate(
                total_income=Sum('amount', filter=Q(transaction_type='income')),
                total_expense=Sum('amount', filter=Q(transaction_type='expense'))
            )
        return queryset.aggregate(
            total_income=Sum('amount', filter=Q(transaction_type='income')),
            total_expense=Sum('amount', filter=Q(transaction_type='expense'))
        )

    def get_user_info(self):
        """Retrieve user details."""
        user = self.request.user
        return {
            'username': user.username,
            'email': user.email,
            'full_name': user.get_full_name()
        }

    def get_last_transaction(self, queryset):
        """Get the most recent transaction for the user."""
        last_transaction = queryset.order_by('-date').first()
        if last_transaction:
            return TransactionSerializer(last_transaction).data
        return None

    def list(self, request, *args, **kwargs):
        """List the filtered transactions and summary statistics."""
        queryset = self.filter_queryset(self.get_queryset())
        total_transaction = self.calculate_totals(queryset)

        income_count = self.count_transactions(queryset, 'income')
        expense_count = self.count_transactions(queryset, 'expense')

        user_wallet = self.get_user_wallet()

        if not user_wallet:
            return Response({"detail": "Wallet not found."}, status=status.HTTP_404_NOT_FOUND)

        # Add additional functionality
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        self.validate_date_range(start_date, end_date)

        date_range_summary = self.get_date_range_summary(queryset, start_date, end_date)
        user_info = self.get_user_info()
        last_transaction = self.get_last_transaction(queryset)
        transaction_categories = self.count_by_category(queryset)

        # Serialize the list of transactions
        page = self.paginate_queryset(queryset)  # Apply pagination to the queryset
        if page is not None:
            transaction_details = self.get_paginated_response(TransactionSerializer(page, many=True).data).data
            paginator_info = self.get_pagination_info(page)
        else:
            transaction_details = TransactionSerializer(queryset, many=True).data
            paginator_info = {}

        result = {
            'income': total_transaction['total_income'] or 0,
            'expense': total_transaction['total_expense'] or 0,
            'balance': user_wallet.balance,
            'income_count': income_count,
            'expense_count': expense_count,
            'total_transactions': queryset.count(),
            'date_range_summary': date_range_summary,
            'user_info': user_info,
            'last_transaction': last_transaction,
            'transaction_categories': transaction_categories,
            'transaction_details': transaction_details  # Added transaction details here
        }

        # Include pagination info if the queryset is paginated
        if paginator_info:
            result.update(paginator_info)

        return Response(result, status=status.HTTP_200_OK)

