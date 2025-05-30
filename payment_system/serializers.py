import logging

from rest_framework import serializers
from .models import Organization

logger = logging.getLogger(__name__)


class BankWebhookSerializer(serializers.Serializer):
    operation_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    payer_inn = serializers.CharField(max_length=12)
    document_number = serializers.CharField(max_length=100)
    document_date = serializers.DateTimeField()

    def validate_amount(self, value) -> float:
        if value <= 0:
            logger.error(f"{self.operation_id} - Amount must be positive {self.amount}")
            raise serializers.ValidationError("Amount must be positive")
        return value


class OrganizationBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['inn', 'balance']
