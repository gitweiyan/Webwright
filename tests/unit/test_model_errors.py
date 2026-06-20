from webwright.utils.model_errors import ModelBillingError, is_billing_error, raise_if_billing_error


def test_is_billing_error_detects_quota_message():
    assert is_billing_error("Error: Insufficient balance for this request")


def test_raise_if_billing_error():
    try:
        raise_if_billing_error(RuntimeError("HTTP 402 Payment Required"))
    except ModelBillingError:
        return
    raise AssertionError("expected ModelBillingError")


def test_raise_if_billing_error_ignores_other_errors():
    try:
        raise_if_billing_error(RuntimeError("connection timeout"))
    except ModelBillingError:
        raise AssertionError("unexpected ModelBillingError")
