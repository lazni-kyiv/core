# access/admin.py
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.admin import GroupAdmin, UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import SetPasswordForm
from django.shortcuts import get_object_or_404, redirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.http import HttpResponse
from django import forms
from unfold.admin import ModelAdmin
from unfold.decorators import action
from unfold.widgets import UnfoldAdminSelectMultipleWidget
import random

from .models import User, UserProfile, LoginLog, ActiveToken

User = get_user_model()
try:
    admin.site.unregister(Group)
except:
    pass


def generate_pin(length=4):
    return ''.join([str(random.randint(0, 9)) for _ in range(length)])


# ── Form ──────────────────────────────────────────────────────────────────────

class CustomUserForm(forms.ModelForm):
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        widget=UnfoldAdminSelectMultipleWidget,
        required=False,
        label='Групи'
    )

    class Meta:
        model = User
        fields = '__all__'


# ── Inline ────────────────────────────────────────────────────────────────────

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    readonly_fields = ['pin_status', 'created_at', 'updated_at', 'password_changed_at', 'pin_changed_at']
    exclude = ['pin_hash']
    verbose_name = "Профіль"
    verbose_name_plural = "Профіль"
    fields = ['pin_status', 'created_at', 'updated_at', 'password_changed_at', 'pin_changed_at']

    def pin_status(self, obj):
        if obj and obj.has_pin():
            return format_html(
                '<span style="color:green; font-weight:bold;">✓ Встановлений</span>'
            )
        return format_html(
            '<span style="color:#e53e3e;">✗ Не встановлений</span>'
        )

    pin_status.short_description = 'Статус ПІН'


# ── UserAdmin ─────────────────────────────────────────────────────────────────

@admin.register(User)
class CustomUserAdmin(BaseUserAdmin, ModelAdmin):
    form = CustomUserForm
    inlines = [UserProfileInline]
    list_display = ['username', 'email', 'first_name', 'last_name', 'display_groups', 'pin_status', 'is_active',
                    'is_staff']

    def display_groups(self, obj):
        groups = obj.groups.all()
        if not groups:
            return '-'
        return ', '.join([g.name for g in groups])

    display_groups.short_description = 'Групи'

    list_filter = ['is_active', 'is_staff']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    readonly_fields = ['date_joined', 'last_login', 'action_buttons_detail']

    fieldsets = (
        ('Особисті дані', {
            'fields': ('username', 'email', 'first_name', 'last_name')
        }),
        ('Права доступу', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups')
        }),
        ('Важливі дати', {
            'fields': ('last_login', 'date_joined')
        }),
        ('Дії', {
            'fields': ('action_buttons_detail',)
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
    )

    # ── Custom URLs ───────────────────────────────────────────────────────────

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('<str:user_id>/reset-pin/',
                 self.admin_site.admin_view(self.reset_pin_view),
                 name='auth_user_reset_pin'),
            path('<str:user_id>/change-password/',
                 self.admin_site.admin_view(self.change_password_view),
                 name='auth_user_change_password'),
        ]
        return custom + urls

    def reset_pin_view(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        profile, _ = UserProfile.objects.get_or_create(user=user)
        pin = generate_pin()
        profile.set_pin(pin)
        self.message_user(
            request,
            format_html(
                'Новий ПІН-код для <strong>{}</strong>: '
                '<strong style="font-size:1.2em; letter-spacing:3px; '
                'background:#f0f0f0; padding:2px 8px; border-radius:4px;">'
                '{}</strong>',
                user.username, pin
            ),
            level='success'
        )
        referer = request.META.get('HTTP_REFERER', '')
        if referer:
            return redirect(referer)
        return redirect(reverse('admin:cloud_auth_user_change', args=[user_id]))

    def change_password_view(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)

        if request.method == 'POST':
            form = SetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                self.message_user(
                    request,
                    format_html('Пароль для <strong>{}</strong> успішно змінено.', user.username),
                    level='success'
                )
                return redirect(reverse('admin:cloud_auth_user_change', args=[user_id]))
        else:
            form = SetPasswordForm(user)

        from django.middleware.csrf import get_token
        csrf_token = get_token(request)
        back_url = reverse('admin:cloud_auth_user_change', args=[user_id])

        content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Змінити пароль — {user.username}</title>
            <style>
                body {{ font-family: system-ui, -apple-system, sans-serif; background: #f5f5f5; margin: 0; padding: 24px; }}
                .wrap {{ max-width: 480px; margin: 40px auto; background: white; border-radius: 12px; padding: 32px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
                h2 {{ margin: 0 0 8px 0; font-size: 24px; font-weight: 500; color: #1a1a1a; }}
                .user-info {{ color: #666; margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid #e5e5e5; }}
                input[type=password] {{ width: 100%; padding: 10px 12px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 14px; box-sizing: border-box; margin-bottom: 12px; }}
                input[type=password]:focus {{ outline: none; border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59,130,246,0.1); }}
                .helptext {{ font-size: 12px; color: #6b7280; margin-top: -8px; margin-bottom: 16px; display: block; }}
                .actions {{ display: flex; gap: 12px; margin-top: 24px; }}
                .btn-save {{ padding: 10px 24px; background: #1d4641; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 500; }}
                .btn-save:hover {{ background: #0f3531; }}
                .btn-cancel {{ padding: 10px 24px; background: #f3f4f6; color: #1d4641; border-radius: 8px; text-decoration: none; font-size: 14px; font-weight: 500; }}
                .btn-cancel:hover {{ background: #e5e7eb; }}
                .errorlist {{ color: #e53e3e; font-size: 13px; margin: 4px 0; padding-left: 0; list-style: none; }}
            </style>
        </head>
        <body>
            <div class="wrap">
                <h2>Змінити пароль</h2>
                <div class="user-info"><strong>{user.username}</strong> ({user.email})</div>
                <form method="post">
                    <input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}">
                    {form.as_p()}
                    <div class="actions">
                        <button type="submit" class="btn-save">Зберегти пароль</button>
                        <a href="{back_url}" class="btn-cancel">Скасувати</a>
                    </div>
                </form>
            </div>
        </body>
        </html>
        """
        return HttpResponse(content)

    # ── Display helpers ───────────────────────────────────────────────────────

    def pin_status(self, obj):
        try:
            has_pin = obj.profile.has_pin() if hasattr(obj, 'profile') else False
        except UserProfile.DoesNotExist:
            has_pin = False
        if has_pin:
            return format_html('<span style="color:#10b981; font-weight:bold;">✓</span>')
        return format_html('<span style="color:#e53e3e;">✗</span>')

    pin_status.short_description = 'ПІН'

    def action_buttons_detail(self, obj):
        if not obj or not obj.pk:
            return '—'
        reset_url = reverse('admin:auth_user_reset_pin', args=[obj.pk])
        password_url = reverse('admin:auth_user_change_password', args=[obj.pk])
        return format_html(
            '<div style="display:flex; gap:12px;">'
            '<a href="{}" style="padding:8px 20px; background:#1d4641; color:#fff; border-radius:8px; text-decoration:none;">'
            'Скинути ПІН-код</a>'
            '<a href="../password/" style="padding:8px 20px; background:#1d4641; color:#fff; border-radius:8px; text-decoration:none;">'
            'Змінити пароль</a>'
            '</div>',
            reset_url, password_url
        )

    action_buttons_detail.short_description = 'Швидкі дії'

    # ── Save / Response ───────────────────────────────────────────────────────

    def save_model(self, request, obj, form, change):
        is_new = not change
        super().save_model(request, obj, form, change)
        profile, _ = UserProfile.objects.get_or_create(user=obj)
        if is_new or not profile.has_pin():
            pin = generate_pin()
            profile.set_pin(pin)
            request.session['generated_pin'] = pin
            request.session['generated_pin_user'] = obj.email

    def response_add(self, request, obj, post_url_continue=None):
        response = super().response_add(request, obj, post_url_continue)
        pin = request.session.pop('generated_pin', None)
        email = request.session.pop('generated_pin_user', None)
        if pin:
            self.message_user(
                request,
                format_html(
                    'Користувач <strong>{}</strong> створений.<br>'
                    'ПІН-код: <strong style="font-size:1.2em; letter-spacing:3px;">{}</strong><br>'
                    '<small style="color:#666;">Збережіть цей код — він більше не буде показаний</small>',
                    email, pin
                ),
                level='success'
            )
        return response

    @action(description='Скинути ПІН-код')
    def reset_pin(self, request, queryset):
        for user in queryset:
            profile, _ = UserProfile.objects.get_or_create(user=user)
            pin = generate_pin()
            profile.set_pin(pin)
            self.message_user(
                request,
                format_html('✅ <strong>{}</strong>: новий ПІН-код <strong>{}</strong>', user.username, pin),
                level='success'
            )

    actions = ['reset_pin']


# ── Group Admin ───────────────────────────────────────────────────────────────

@admin.register(Group)
class UnfoldGroupAdmin(GroupAdmin, ModelAdmin):
    pass


# ── ActiveToken Admin ─────────────────────────────────────────────────────────

@admin.register(ActiveToken)
class ActiveTokenAdmin(ModelAdmin):
    list_display = ['user_email', 'token_type', 'revoked', 'created_at', 'expires_at']
    list_filter = ['token_type', 'revoked']
    search_fields = ['user__email', 'jti']
    readonly_fields = ['user', 'jti', 'token_type', 'created_at', 'expires_at']

    def user_email(self, obj):
        return obj.user.email

    user_email.short_description = 'Email'
    user_email.admin_order_field = 'user__email'

    def is_valid_display(self, obj):
        if obj.is_valid():
            return format_html('<span style="color:#10b981;">✓ Валідний</span>')
        return format_html('<span style="color:#e53e3e;">✗ Невалідний</span>')

    is_valid_display.short_description = 'Статус'

    @action(description='Анулювати вибрані токени')
    def revoke_selected(self, request, queryset):
        count = queryset.update(revoked=True)
        self.message_user(request, f'✅ Анульовано {count} токенів', level='success')

    actions = ['revoke_selected']

    def has_add_permission(self, request):
        return False


# ── LoginLog Admin ────────────────────────────────────────────────────────────

@admin.register(LoginLog)
class LoginLogAdmin(ModelAdmin):
    list_display = ['email', 'action', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['email','user__email']
    readonly_fields = ['user', 'email', 'action', 'created_at']

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser