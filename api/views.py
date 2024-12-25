from django.forms import ValidationError
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from api.models import Wallet, Transaction, UserProfile
from api.serialaizer import WalletSerializer, TransactionSerializer, UserProfileSerializer
from django.db.models import Sum, Q
from rest_framework.pagination import PageNumberPagination
from django.db.models import Sum
from rest_framework import filters
from rest_framework.response import Response
from .models import Transaction

# Pagination
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class WalletListView(generics.ListCreateAPIView):
    serializer_class = WalletSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return Wallet.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class WalletDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = WalletSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Wallet.objects.filter(user=self.request.user)

class TransactionListView(generics.ListCreateAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return Transaction.objects.filter(wallet__user=self.request.user)

    def perform_create(self, serializer):
        user_wallet = Wallet.objects.get(user=self.request.user)
        serializer.save(wallet=user_wallet)  






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


from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import UserProfile
# from .s import UserProfileSerializer

@method_decorator(cache_page(60 * 5), name='dispatch')  # Кеш барои 5 дақиқа
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
from .serialaizer import TransactionSerializer  # Fixed typo: 'serialaizer' should be 'serializers'
from django_filters import rest_framework as filters
from rest_framework.pagination import PageNumberPagination


# Filter for transactions
class TransactionFilter(filters.FilterSet):
    day = filters.NumberFilter(field_name='date__day')
    month = filters.NumberFilter(field_name='date__month')
    year = filters.NumberFilter(field_name='date__year')

    class Meta:
        model = Transaction
        fields = ['day', 'month', 'year']




# Pagination class for the API
class CustomPagination(PageNumberPagination):
    page_size = 10  # Set the number of items per page
    page_size_query_param = 'page_size'
    max_page_size = 100  # Maximum items per page


class ReportView(generics.ListAPIView):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = TransactionFilter

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

    def count_by_category(self, queryset):
        """Count transactions by categories."""
        return queryset.values('category').annotate(count=Count('id'))

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
        return TransactionSerializer(last_transaction).data if last_transaction else None

    def get_pagination_info(self, page):
        """Get pagination data."""
        if not page or isinstance(page, list):  # If it's a list (no pagination), return an empty dict
            return {}

        return {
            'current_page': page.number,
            'total_pages': page.paginator.num_pages,
            'total_items': page.paginator.count
        }

    def validate_and_adjust_dates(self, day, month, year):
        """Validate and adjust the dates if day is provided but month/year is missing."""

        # Вақте ки танҳо рӯз ворид мешавад ва моҳ нест
        if day and not month:
            raise ValidationError("Month is required when day is provided.")

        # Вақте ки рӯз ва моҳ ворид мешаванд, вале сол нест
        if day and month and not year:
            raise ValidationError("Year is required when both day and month are provided.")

        # Вақте ки моҳ ворид мешавад, солро низ талаб мекунем
        if month and not year:
            raise ValidationError("Year is required when month is provided.")

        # Вақте ки ҳамаи 3 филтри рӯзи, моҳ ва сол ворид мешаванд
        if day and month and year:
            return Q(date__day=day, date__month=month, date__year=year)

        # Вақте ки танҳо моҳ ва сол ворид шудаанд
        elif month and year:
            return Q(date__month=month, date__year=year)

        # Вақте ки танҳо сол ворид шудааст
        elif year:
            return Q(date__year=year)

        return Q()  # Агар ҳеҷ як филтри таърихро ворид накарданд

    def list(self, request, *args, **kwargs):
        """List the filtered transactions and summary statistics."""
        queryset = self.filter_queryset(self.get_queryset())

        # Get the day, month, and year from request
        day = request.GET.get('day')
        month = request.GET.get('month')
        year = request.GET.get('year')

        # Validate and adjust dates if necessary
        try:
            date_filter = self.validate_and_adjust_dates(day, month, year)
            queryset = queryset.filter(date_filter)
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Retrieve total amounts and counts
        total_transaction = self.calculate_totals(queryset)
        income_count = self.count_transactions(queryset, 'income')
        expense_count = self.count_transactions(queryset, 'expense')

        # Get user wallet and transaction details
        user_wallet = self.get_user_wallet()
        if not user_wallet:
            return Response({"detail": "Wallet not found."}, status=status.HTTP_404_NOT_FOUND)

        # Get summary of date range (if any)
        date_range_summary = self.calculate_totals(queryset)
        user_info = self.get_user_info()
        last_transaction = self.get_last_transaction(queryset)
        transaction_categories = self.count_by_category(queryset)

        # Paginate the queryset
        page = self.paginate_queryset(queryset)
        if page is not None:
            transaction_details = self.get_paginated_response(TransactionSerializer(page, many=True).data).data
            paginator_info = self.get_pagination_info(page)  # Get pagination info
        else:
            transaction_details = TransactionSerializer(queryset, many=True).data
            paginator_info = {}

        # Prepare final result
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
            'transaction_details': transaction_details
        }

        # Include pagination info if the queryset is paginated
        if paginator_info:
            result.update(paginator_info)

        return Response(result, status=status.HTTP_200_OK)
