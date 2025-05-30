from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Organization
from .serializers import (
    BankWebhookSerializer,
    OrganizationBalanceSerializer
)
from .services import PaymentService


class BankWebhookView(APIView):
    def post(self, request) -> Response:
        serializer = BankWebhookSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        PaymentService.process_payment(serializer.validated_data)
        return Response(status=status.HTTP_200_OK)


class OrganizationBalanceView(APIView):
    def get(self, request, inn: str) -> Response:
        try:
            org = Organization.objects.get(inn=inn)
            serializer = OrganizationBalanceSerializer(org)
            return Response(serializer.data)
        except Organization.DoesNotExist:
            return Response(
                {"detail": "Organization not found"},
                status=status.HTTP_404_NOT_FOUND
            )