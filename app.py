import datetime

from flask import Flask, render_template, request, url_for, redirect, make_response
from flask_sqlalchemy import SQLAlchemy
from hashlib import sha256
import requests
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
secret_key = "SecretKey01"
db = SQLAlchemy(app)


class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    currency = db.Column(db.String(3), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, default='')
    time = db.Column(db.DateTime, default=datetime.datetime.utcnow())


db.create_all()


def get_sign(*args):
    """Принимает на вход аргументы типа str,
    Склеивает через ":" и добавляет в конец secret_key
    Возвращает строку закодированную через sha256 в 16-ном формате
    """
    clear_sign = ":".join(args)
    clear_sign += secret_key
    sign = sha256(clear_sign.encode('utf-8')).hexdigest()
    return sign


@app.route('/', methods=['GET', 'POST'])
def hello_world():
    if request.method == 'GET':
        return render_template('main.html')
    elif request.method == 'POST':
        currency = request.form.get('cur')
        sum_ = f"{float(request.form.get('sum')):.2f}"
        description = request.form.get('description')
        log = Log(currency=currency, amount=sum_, description=description, time=datetime.datetime.utcnow())
        db.session.add(log)
        db.session.commit()
        if currency == 'EUR':
            sign = get_sign(sum_, '978', '5', str(Log.time))
            context = {'sum': sum_, 'description': description, "shop_order_id": Log.time, 'sign': sign}
            return render_template('pay_method.html', **context)

        elif currency == 'USD':
            sign = get_sign('840', sum_, '840', '5', str(Log.time))

            payload = json.dumps(
                {"description": description, "payer_currency": 840, "shop_amount": sum_, "shop_currency": 840,
                 "shop_id": "5", "shop_order_id": str(Log.time), "sign": sign})
            response = requests.post('https://core.piastrix.com/bill/create', data=payload,
                                     headers=({'Content-Type': 'application/json'})).json()
            if response['error_code'] == 0:
                return redirect(response['data']['url'])
            else:
                return make_response('', 404)
        elif currency == 'RUB':
            sign = get_sign(sum_, '643', "advcash_rub", "5", str(Log.time))
            payload = json.dumps(
                {"description": description, "amount": sum_, "currency": "643",
                 "shop_id": "5", "shop_order_id": str(Log.time), "payway": "advcash_rub", "sign": sign})

            response = requests.post('https://core.piastrix.com/invoice/create', data=payload,
                                     headers=({'Content-Type': 'application/json'})).json()
            inputs = list(response['data']['data'].items())


            context = {'inputs': inputs, 'action': response['data']['url'], 'method': response['data']['method']}
            return render_template('i_method.html', **context)


if __name__ == '__main__':
    app.run()
