import logging

from django.shortcuts import render, redirect
from django import http
import re
from .models import User
from django.db import DatabaseError
from django.urls import reverse
from django.contrib.auth import login
from django_redis import get_redis_connection

# Create your views here.
from django.views import View
from Dd_mall.utils.response_code import RETCODE, err_msg


class CheckUsernameRepeatView(View):
    def get(self, request, username):
        """校验用户名是否重复"""
        count = User.objects.filter(username=username).count()
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': err_msg.get(RETCODE.OK), 'count': count})


class CheckMobileRepeatView(View):
    def get(self, request, num):
        """校验手机号是否重复"""
        count = User.objects.filter(mobile=num).count()
        if count == 1:
            redis_coon = get_redis_connection('verify_code')
            redis_coon.setex('r_%s' % num, 360, '1')
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': err_msg.get(RETCODE.OK), 'count': count})


class RegisterView(View):
    """用户注册"""

    def get(self, request):
        """提供用户注册页面"""
        return render(request, 'register.html')

    def post(self, request):
        """实现用户注册业务逻辑"""
        username = request.POST.get('username')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        mobile = request.POST.get('mobile')
        sms_code = request.POST.get('sms_code')
        allow = request.POST.get('allow')

        if not all([username, password1, password2, mobile, allow]):
            return http.HttpResponseForbidden('缺少参数')

        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$', username):
            return http.HttpResponseForbidden('用户名不合法')

        if not re.match(r'^[a-zA-Z0-9]{8,20}$', password1):
            return http.HttpResponseForbidden('密码不合法')

        if password1 != password2:
            return http.HttpResponseForbidden('两次输入密码不一致')

        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('手机号码不合法')

        redis_coon = get_redis_connection('verify_code')
        sms_code_server = redis_coon.get('sms_%s' % mobile)
        if sms_code_server is None:
            return render(request, 'register.html', {'register_errmsg': '短信验证码已失效'})

        if not (sms_code.lower() == sms_code.lower()):
            return render(request, 'register.html', {'register_errmsg': '短信验证码输入有误'})

        if allow != 'on':
            return http.HttpResponseForbidden('请勾选用户协议')
        try:
            user = User.objects.create_user(username=username, password=password1, mobile=mobile)
        except DatabaseError:
            return render(request, 'register.html', {'register_errmsg': '注册失败'})

        login(request, user)

        return redirect(reverse('contents:index'))
