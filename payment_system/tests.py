from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Organization, Payment, BalanceLog
import uuid
from datetime import datetime, timezone


class PaymentAPITests(APITestCase):
    def setUp(self):
        # Создаем тестовую организацию
        self.org_inn = "1234567890"
        self.organization = Organization.objects.create(
            inn=self.org_inn,
            balance=1000.00
        )

        # Тестовые данные для вебхука
        self.webhook_data = {
            "operation_id": str(uuid.uuid4()),
            "amount": "500.00",
            "payer_inn": self.org_inn,
            "document_number": "PAY-001",
            "document_date": "2024-05-01T12:00"
        }

        self.webhook_url = reverse('bank-webhook')
        self.balance_url = lambda inn: reverse('organization-balance', kwargs={'inn': inn})

    def test_process_valid_webhook(self):
        """Тест обработки валидного вебхука"""
        response = self.client.post(
            self.webhook_url,
            data=self.webhook_data,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверяем, что платеж создан
        payment = Payment.objects.get(operation_id=self.webhook_data['operation_id'])
        self.assertEqual(float(payment.amount), float(self.webhook_data['amount']))

        # Проверяем обновление баланса
        self.organization.refresh_from_db()
        self.assertEqual(float(self.organization.balance), 1500.00)  # 1000 + 500

        # Проверяем лог баланса
        balance_log = BalanceLog.objects.get(payment=payment)
        self.assertEqual(float(balance_log.previous_balance), 1000.00)
        self.assertEqual(float(balance_log.new_balance), 1500.00)

    def test_duplicate_webhook(self):
        """Тест обработки дубликата вебхука"""
        # Первый запрос
        response1 = self.client.post(
            self.webhook_url,
            data=self.webhook_data,
            format='json'
        )
        self.assertEqual(response1.status_code, status.HTTP_200_OK)

        # Второй запрос с теми же данными
        response2 = self.client.post(
            self.webhook_url,
            data=self.webhook_data,
            format='json'
        )
        self.assertEqual(response2.status_code, status.HTTP_200_OK)

        # Должен быть только один платеж
        payments_count = Payment.objects.filter(
            operation_id=self.webhook_data['operation_id']
        ).count()
        self.assertEqual(payments_count, 1)

        # Баланс не должен измениться во второй раз
        self.organization.refresh_from_db()
        self.assertEqual(float(self.organization.balance), 1500.00)


    def test_webhook_for_new_organization(self):
        """Тест вебхука для новой организации"""
        new_inn = "0987654321"
        webhook_data = {
            **self.webhook_data,
            "operation_id": str(uuid.uuid4()),
            "payer_inn": new_inn
        }

        response = self.client.post(
            self.webhook_url,
            data=webhook_data,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверяем, что организация создана
        org = Organization.objects.get(inn=new_inn)
        self.assertEqual(float(org.balance), float(webhook_data['amount']))

    def test_get_existing_organization_balance(self):
        """Тест получения баланса существующей организации"""
        response = self.client.get(self.balance_url(self.org_inn))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['inn'], self.org_inn)
        self.assertEqual(float(response.data['balance']), float(self.organization.balance))

    def test_get_nonexistent_organization_balance(self):
        """Тест получения баланса несуществующей организации"""
        non_existent_inn = "0000000000"
        response = self.client.get(self.balance_url(non_existent_inn))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['detail'], 'Organization not found')

    def test_balance_after_multiple_payments(self):
        """Тест баланса после нескольких платежей"""
        # Первый платеж
        webhook_data1 = {
            **self.webhook_data,
            "operation_id": str(uuid.uuid4()),
            "amount": "200.00"
        }
        response1 = self.client.post(
            self.webhook_url,
            data=webhook_data1,
            format='json'
        )
        self.assertEqual(response1.status_code, status.HTTP_200_OK)

        # Второй платеж
        webhook_data2 = {
            **self.webhook_data,
            "operation_id": str(uuid.uuid4()),
            "amount": "300.00"
        }
        response2 = self.client.post(
            self.webhook_url,
            data=webhook_data2,
            format='json'
        )
        self.assertEqual(response2.status_code, status.HTTP_200_OK)

        # Проверяем баланс
        response = self.client.get(self.balance_url(self.org_inn))
        self.assertEqual(float(response.data['balance']), 1500.00)  # 1000 + 200 + 300

    def test_full_flow(self):
        """Полный тест потока: вебхук -> проверка баланса"""
        # Исходный баланс
        response_before = self.client.get(self.balance_url(self.org_inn))
        self.assertEqual(float(response_before.data['balance']), 1000.00)

        # Отправляем вебхук
        webhook_data = {
            **self.webhook_data,
            "operation_id": str(uuid.uuid4()),
            "amount": "750.50"
        }
        response_webhook = self.client.post(
            self.webhook_url,
            data=webhook_data,
            format='json'
        )
        self.assertEqual(response_webhook.status_code, status.HTTP_200_OK)

        # Проверяем обновленный баланс
        response_after = self.client.get(self.balance_url(self.org_inn))
        self.assertEqual(float(response_after.data['balance']), 1750.50)  # 1000 + 750.50

        # Проверяем данные в БД
        payment = Payment.objects.get(operation_id=webhook_data['operation_id'])
        self.assertEqual(float(payment.amount), 750.50)

        balance_log = BalanceLog.objects.get(payment=payment)
        self.assertEqual(float(balance_log.previous_balance), 1000.00)
        self.assertEqual(float(balance_log.new_balance), 1750.50)

    def test_large_amount(self):
        """Тест обработки очень большой суммы"""
        webhook_data = {
            **self.webhook_data,
            "operation_id": str(uuid.uuid4()),
            "amount": "999999999999.99"
        }

        response = self.client.post(
            self.webhook_url,
            data=webhook_data,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверяем баланс
        response_balance = self.client.get(self.balance_url(self.org_inn))
        self.assertEqual(float(response_balance.data['balance']), 1000000000999.99)
