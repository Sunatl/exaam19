from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Sum
from datetime import datetime


# CustomUser Model
class CustomUser(AbstractUser):
    def __str__(self):
        return self.username


class UserProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
    salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"Profile of {self.user.username}"

    def save(self, *args, **kwargs):
        is_new_salary = False
        if self.pk:  # Check if the object already exists
            old_instance = UserProfile.objects.filter(pk=self.pk).first()
            if old_instance and old_instance.salary != self.salary:
                is_new_salary = True
        else:
            is_new_salary = True  # Treat as new for objects being created

        # Only update the wallet and create a transaction if the salary is new or updated
        if is_new_salary and self.salary > 0:
            if hasattr(self.user, 'wallet'):  # Ensure the user has a wallet
                # Create a transaction for the new salary
                transaction = Transaction.objects.create(
                    wallet=self.user.wallet,
                    amount=self.salary,
                    transaction_type='income',
                    category='other',
                    description=f"Salary for {self.user.username}",
                )

                # Now update the wallet balance after the transaction is created
                self.user.wallet.update_balance(self.salary)  # This will add salary to the wallet balance

        super().save(*args, **kwargs)




# Wallet Model
class Wallet(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"Wallet of {self.user.username}"

    def update_balance(self, amount):
        """Update the wallet balance by the given amount."""
        self.balance += amount
        self.save()


# Transaction Model
class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('income', 'Income'),
        ('expense', 'Expense'),
    )

    CATEGORY_CHOICES = (
        ('food', 'Food'),
        ('transport', 'Transport'),
        ('entertainment', 'Entertainment'),
        ('other', 'Other'),
    )

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=7, choices=TRANSACTION_TYPES)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    description = models.TextField(blank=True, null=True)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_type.capitalize()} - {self.amount} - {self.wallet.user.username}"

    def save(self, *args, **kwargs):
        """Update wallet balance when a transaction is created."""
        if self.pk is None:  # Only update balance for new transactions
            if self.transaction_type == 'expense':
                self.wallet.update_balance(-self.amount)
            elif self.transaction_type == 'income':
                self.wallet.update_balance(self.amount)
        super().save(*args, **kwargs)


# Signals to create Wallet and Profile when CustomUser is created
@receiver(post_save, sender=CustomUser)
def create_wallet_and_profile(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.create(user=instance)
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=CustomUser)
def save_wallet_and_profile(sender, instance, **kwargs):
    if hasattr(instance, 'wallet'):
        instance.wallet.save()
    if hasattr(instance, 'profile'):
        instance.profile.save()
