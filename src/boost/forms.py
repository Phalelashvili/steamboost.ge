from django import forms


class t_boost_form(forms.Form):
    steam_username = forms.CharField()
    steam_password = forms.CharField()
    authcode = forms.CharField(required=False)
    identity_secret = forms.CharField(required=False)
    shared_secret = forms.CharField(required=False)
    trade_amount = forms.IntegerField(min_value=250, max_value=50000,)


class c_boost_form(forms.Form):
    comment_amount = forms.IntegerField(min_value=6, max_value=1000)
    comment = forms.CharField(max_length=999, required=False)
    delay = forms.IntegerField(min_value=0, max_value=1440, required=False)


class h_boost_form(forms.Form):
    steam_username = forms.CharField()
    steam_password = forms.CharField()
    auth_code = forms.CharField()
    free = forms.BooleanField(required=False)
    boost_time = forms.IntegerField(min_value=1, max_value=1000,)
    games_id = forms.CharField()


class a_boost_form(forms.Form):
    sharedID = forms.CharField(max_length=70)
    favAmount = forms.IntegerField(min_value=10, max_value=1000)
    likeAmount = forms.IntegerField(min_value=10, max_value=1000)
