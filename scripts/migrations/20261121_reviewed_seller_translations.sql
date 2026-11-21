-- Проверенные переводы Codex сохраняются независимо от версии словаря.
ALTER TABLE seller_description_translations
    DROP CONSTRAINT seller_description_translations_status_check,
    DROP CONSTRAINT seller_description_translations_check1;

ALTER TABLE seller_description_translations
    ADD CONSTRAINT seller_description_translations_status_check
        CHECK (status IN ('pending', 'dictionary', 'untranslated', 'original', 'reviewed')),
    ADD CONSTRAINT seller_description_translations_check1
        CHECK ((status IN ('dictionary', 'reviewed') AND translated_text IS NOT NULL)
            OR (status NOT IN ('dictionary', 'reviewed') AND translated_text IS NULL));

