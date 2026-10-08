from django.shortcuts import redirect


# Restricts Stock Viewer requests centrally; allowed view names must match app URL names.
class StockViewerAccessMiddleware:
    allowed_view_names = {"real_time_stock", "real_time_stock_data", "logout"}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.user.is_authenticated and request.user.is_stock_viewer:
            if request.resolver_match.view_name not in self.allowed_view_names:
                return redirect("real_time_stock")