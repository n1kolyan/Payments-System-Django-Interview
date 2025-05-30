from django.db import models


class Organization(models.Model):
    inn = models.CharField(max_length=12, unique=True, db_index=True)
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"

    def __str__(self):
        return f"{self.inn} (Balance: {self.balance})"


class Payment(models.Model):
    operation_id = models.UUIDField(unique=True, db_index=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    payer_inn = models.CharField(max_length=12)
    document_number = models.CharField(max_length=100)
    document_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment {self.operation_id} ({self.amount})"


class BalanceLog(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    previous_balance = models.DecimalField(max_digits=15, decimal_places=2)
    new_balance = models.DecimalField(max_digits=15, decimal_places=2)
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Balance Log"
        verbose_name_plural = "Balance Logs"
        ordering = ['-created_at']

    def __str__(self):
        return f"Balance update for {self.organization.inn}"
