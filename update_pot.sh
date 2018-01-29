#!/usr/bin/env bash
pybabel extract -F babel.cfg -o locales/changeswithin.pot ./
msgfmt -o locales/ca/LC_MESSAGES/messages.mo locales/ca/LC_MESSAGES/messages.po
msgfmt -o locales/en/LC_MESSAGES/messages.mo locales/en/LC_MESSAGES/messages.po
msgfmt -o locales/es/LC_MESSAGES/messages.mo locales/es/LC_MESSAGES/messages.po