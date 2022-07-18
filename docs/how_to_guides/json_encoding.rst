.. _json_encoding:

JSON Encoding
=============

It is often useful to be able to control how objects are encoded to
and decoded from JSON. Quart makes this possible via a JSONProvider
:class:`~quart.json.provider.JSONProvider`.

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
    from quart.json.provider import _default, DefaultJSONProvider


    class MoneyJSONProvider(DefaultJSONProvider):

        @staticmethod
        def default(object_):
            if isinstance(object_, date):
                return http_date(object_)
            if isinstance(object_, (Decimal, UUID)):
                return str(object_)
            if is_dataclass(object_):
                return asdict(object_)
            if hasattr(object_, "__html__"):
                return str(object_.__html__())
            if isinstance(object_, Money):
                return {'amount': object_.amount, 'currency': object_.currency}

            raise TypeError(f"Object of type {type(object_).__name__} is not JSON serializable")

        @staticmethod
        def dict_to_object(dict_):
            if 'amount' in dict_ and 'currency' in dict_:
                return Money(Decimal(dict_['amount']), dict_['currency'])
            else:
                return dict_

        def loads(self, object_, **kwargs):
            return super().loads(object_, object_hook=self.dict_to_object, **kwargs)
