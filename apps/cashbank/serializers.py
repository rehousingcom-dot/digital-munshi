from rest_framework import serializers
from .models import BankAccount, BankTransaction, Cheque, LoanAccount, ExpenseCategory, Expense


class BankAccountSerializer(serializers.ModelSerializer):
    balance = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = BankAccount
        fields = "__all__"


class BankTransactionSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source="account.name", read_only=True)

    class Meta:
        model = BankTransaction
        fields = "__all__"


class ChequeSerializer(serializers.ModelSerializer):
    party_name = serializers.CharField(source="party.name", read_only=True, default="")

    class Meta:
        model = Cheque
        fields = "__all__"


class LoanAccountSerializer(serializers.ModelSerializer):
    emi = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    total_payable = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    total_interest = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = LoanAccount
        fields = "__all__"


class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = "__all__"


class ExpenseSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True, default="")
    total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = Expense
        fields = "__all__"
