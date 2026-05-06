class DocumentTemplateService:
    def match_template(self, text: str) -> str | None:
        normalized = text.lower()
        if "счет" in normalized or "счёт" in normalized:
            return self.invoice_template()
        if "акт" in normalized:
            return self.act_template()
        if "договор" in normalized:
            return self.contract_template()
        if "мой налог" in normalized or "чек" in normalized:
            return self.my_tax_receipt_guide()
        if "платежк" in normalized or "платёжк" in normalized:
            return self.tax_payment_template()
        return None

    @staticmethod
    def invoice_template() -> str:
        return (
            "Шаблон счета на оплату\n"
            "1. Поставщик: ФИО/ИП, ИНН, реквизиты\n"
            "2. Покупатель: ФИО/компания\n"
            "3. Основание: счет №___ от __.__.____\n"
            "4. Услуга/товар: ______\n"
            "5. Сумма: ______ ₽\n"
            "6. Без НДС / с НДС ___%\n"
            "7. Срок оплаты: ______\n"
            "8. Подпись/ФИО"
        )

    @staticmethod
    def act_template() -> str:
        return (
            "Шаблон акта выполненных работ\n"
            "Акт №___ от __.__.____\n"
            "Исполнитель: ______\n"
            "Заказчик: ______\n"
            "Услуги: ______\n"
            "Период: ______\n"
            "Сумма: ______ ₽\n"
            "Стороны претензий не имеют.\n"
            "Подписи сторон"
        )

    @staticmethod
    def contract_template() -> str:
        return (
            "Краткий договор оказания услуг\n"
            "1. Предмет: исполнитель оказывает услуги ______.\n"
            "2. Срок: с __.__.____ по __.__.____.\n"
            "3. Стоимость: ______ ₽.\n"
            "4. Оплата: в течение ___ дней после счета/акта.\n"
            "5. Приемка: по акту выполненных работ.\n"
            "6. Ответственность: по ГК РФ.\n"
            "7. Реквизиты и подписи сторон."
        )

    @staticmethod
    def my_tax_receipt_guide() -> str:
        return (
            "Как выдать чек через «Мой налог»\n"
            "1. Открой приложение «Мой налог».\n"
            "2. Нажми «Новая продажа».\n"
            "3. Укажи сумму, дату и кто заплатил: физлицо или компания/ИП.\n"
            "4. Сохрани чек.\n"
            "5. Отправь чек клиенту ссылкой или PDF."
        )

    @staticmethod
    def tax_payment_template() -> str:
        return (
            "Шаблон платежки на уплату налога\n"
            "Получатель: Казначейство России / УФК по региону\n"
            "ИНН/КПП получателя: по данным ФНС\n"
            "КБК: по конкретному налогу\n"
            "ОКТМО: по месту учета\n"
            "Статус плательщика: 09 для ИП / 01 для ООО\n"
            "Назначение платежа: уплата ______ за ______\n"
            "Перед оплатой проверь реквизиты в nalog.ru или в ЕНС."
        )
