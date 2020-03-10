.. _json_encoding:

JSON Encoding
=============

It is often useful to be able to control how objects are encoded to
and decoded from JSON. Quart makes this possible via the
:attr:`~quart.app.Quart.json_encoder` and
:attr:`~quart.app.Quart.json_decoder` to a custom JSONEncoder and
JSONDecoder. This can be done for all routes via the
:class:`~quart.Quart` or for blueprint specific routes via
:attr:`~quart.blueprints.Blueprint.json_encoder` and
:attr:`~quart.blueprints.Blueprint.json_decoder`.

Money example
-------------

As an example lets consider a Money object,

.. code-block:: python

    class Money:

        def __init__(self, amount: Decimal, currency: str) -> None:
            self.amount = amount
            self.currency = currency

which we desire to translate to JSON as,

.. code-block:: json

    {
      "amount": "10.00",
      "currency": "GBP"
    }

using encoders and decoders as so,

.. code-block:: python

    class MoneyJSONEncoder(json.JSONEncoder):

        def default(self, object_):
            if isinstance(object_, Money):
                return {'amount': object_.amount, 'currency': object_.currency}
            else:
                return super().default(object_)

    class MoneyJSONDecoder(json.JSONDecoder):

        def __init__(self, *args, **kwargs):
            super().__init__(object_hook=self.dict_to_object, *args, **kwargs)

        def dict_to_ibject(self, dict_):
            if 'amount' in dict_ and 'currency' in dict_:
                return Money(Decimal(dict_['amount']), dict_['currency'])
            else:
                return dict_

    app.json_decoder = MoneyJSONDecoder
    app.json_encoder = MoneyJSONEncoder
