import json
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Account, LedgerEntry, User
from .services import BadRequest, deposit, withdraw, transfer

def _json_body(request):
    try:
        if not request.body:
            return {}
        return json.loads(request.body)
    except json.JSONDecodeError:
        raise BadRequest("Invalid JSON body", 400)

@csrf_exempt
def api_login(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    data = _json_body(request)
    username = data.get("username")
    password = data.get("password")
    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)
        return JsonResponse({"status": "logged_in", "username": user.username, "role": user.role})
    return JsonResponse({"error": "Invalid credentials"}, status=401)

@csrf_exempt
def api_logout(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    logout(request)
    return JsonResponse({"status": "logged_out"})

def api_accounts(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    
    user = request.user
    if user.role == User.Role.ADMIN or user.role == User.Role.AUDITOR:
        accounts = Account.objects.all()
    else:
        accounts = Account.objects.filter(owner=user)
    
    data = [{"id": a.id, "owner_id": a.owner_id, "name": a.name, "balance": a.balance} for a in accounts]
    return JsonResponse({"accounts": data})

def api_statement(request, account_id):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    
    try:
        account = Account.objects.get(id=account_id)
    except Account.DoesNotExist:
        return JsonResponse({"error": "Account not found"}, status=404)
    
    user = request.user
    if user.role != User.Role.ADMIN and user.role != User.Role.AUDITOR and account.owner_id != user.id:
        return JsonResponse({"error": "Not allowed to view this statement"}, status=403)
    
    entries = account.entries.all().order_by("created_at")
    history = [{
        "id": e.id,
        "kind": e.kind,
        "status": e.status,
        "amount": e.amount,
        "balance_after": e.balance_after,
        "transfer_id": str(e.transfer_id) if e.transfer_id else None,
        "initiated_by": e.initiated_by.username,
        "idempotency_key": e.idempotency_key,
        "reason": e.reason,
        "created_at": e.created_at.isoformat()
    } for e in entries]
    
    return JsonResponse({"account_id": account.id, "balance": account.balance, "entries": history})

@csrf_exempt
def api_deposit(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    
    key = request.headers.get("Idempotency-Key", "")
    try:
        data = _json_body(request)
        res = deposit(request.user, data.get("account_id"), data.get("amount"), key)
        return JsonResponse(res.body, status=res.http_status)
    except BadRequest as e:
        return JsonResponse({"error": e.message}, status=e.http_status)

@csrf_exempt
def api_withdraw(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    
    key = request.headers.get("Idempotency-Key", "")
    try:
        data = _json_body(request)
        res = withdraw(request.user, data.get("account_id"), data.get("amount"), key)
        return JsonResponse(res.body, status=res.http_status)
    except BadRequest as e:
        return JsonResponse({"error": e.message}, status=e.http_status)

@csrf_exempt
def api_transfer(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    
    key = request.headers.get("Idempotency-Key", "")
    try:
        data = _json_body(request)
        res = transfer(request.user, data.get("from_id"), data.get("to_id"), data.get("amount"), key)
        return JsonResponse(res.body, status=res.http_status)
    except BadRequest as e:
        return JsonResponse({"error": e.message}, status=e.http_status)

# Create your views here.
