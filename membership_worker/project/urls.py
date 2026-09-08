from django.urls import path

from membership_worker.worker import views

urlpatterns = [
    path("internal/health/", views.internal_health_view, name="worker-health"),
    path("internal/orders/", views.internal_orders_view, name="worker-internal-orders"),
    path("internal/orders/<int:job_id>/", views.internal_order_status_view, name="worker-internal-order-status"),
    path("internal/accounts/start-login/", views.internal_start_login_view, name="worker-start-login"),
    path("internal/accounts/verify-code/", views.internal_verify_code_view, name="worker-verify-code"),
    path("internal/accounts/signup/", views.internal_signup_view, name="worker-signup"),
    path("internal/accounts/cancel-login/", views.internal_cancel_login_view, name="worker-cancel-login"),
    path("internal/accounts/available/", views.internal_available_accounts_view, name="worker-available-accounts"),
]
