from django import forms


class deposit_form(forms.Form):
    csgo_item_list = forms.CharField(max_length=9999, required=False)
    tf2_item_list = forms.CharField(max_length=9999, required=False)


class withdraw_form(forms.Form):
    amount = forms.FloatField(min_value=1)
    website = forms.CharField()
    identifier = forms.CharField(min_length=8)
    name = forms.CharField()


class emoneyDeposit_form(forms.Form):
    identifier = forms.CharField()
    amount = forms.FloatField(min_value=0.1)


class update_settings_form(forms.Form):
    gel_price = forms.FloatField()
    min_price = forms.FloatField()
    max_price = forms.FloatField()
    c_boost_price = forms.FloatField()
    h_boost_price = forms.FloatField()
    t_boost_price = forms.FloatField()
    min_sold_amount = forms.FloatField()
    csgo_key_price = forms.FloatField()
    tf2_key_price = forms.FloatField()
    credit_price = forms.FloatField()
    referral_reward = forms.FloatField()
    referral_reward_user = forms.FloatField()
    banned_items = forms.CharField(required=False)
    cboost = forms.CharField()
    hboost = forms.CharField()
    tboost = forms.CharField()
    deposit = forms.CharField()
    withdraw = forms.CharField()
