from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .permissions import IsStaff
from .serializers import StaffLoginSerializer, StaffMeSerializer


class StaffLoginView(TokenObtainPairView):
    serializer_class = StaffLoginSerializer


class StaffRefreshView(TokenRefreshView):
    pass


class StaffMeView(APIView):
    permission_classes = [IsAuthenticated, IsStaff]

    def get(self, request):
        return Response(StaffMeSerializer(request.user).data)
