"""Tests for backend.services.document_templates."""

from backend.services.document_templates import DocumentTemplateService


def test_match_invoice():
    svc = DocumentTemplateService()
    result = svc.match_template("покажи шаблон счёта")
    assert result is not None
    assert "Шаблон счета" in result


def test_match_act():
    svc = DocumentTemplateService()
    result = svc.match_template("нужен акт")
    assert result is not None
    assert "Акт" in result


def test_match_contract():
    svc = DocumentTemplateService()
    result = svc.match_template("покажи договор")
    assert result is not None
    assert "договор" in result.lower()


def test_match_my_tax_receipt():
    svc = DocumentTemplateService()
    result = svc.match_template("как выдать чек")
    assert result is not None
    assert "Мой налог" in result


def test_match_payment_order():
    svc = DocumentTemplateService()
    result = svc.match_template("шаблон платежки")
    assert result is not None
    assert "платежк" in result.lower()


def test_match_none():
    svc = DocumentTemplateService()
    assert svc.match_template("привет") is None


def test_invoice_template():
    t = DocumentTemplateService.invoice_template()
    assert "Поставщик" in t


def test_act_template():
    t = DocumentTemplateService.act_template()
    assert "Исполнитель" in t


def test_contract_template():
    t = DocumentTemplateService.contract_template()
    assert "Предмет" in t


def test_my_tax_receipt_guide():
    t = DocumentTemplateService.my_tax_receipt_guide()
    assert "Мой налог" in t


def test_tax_payment_template():
    t = DocumentTemplateService.tax_payment_template()
    assert "Казначейство" in t
