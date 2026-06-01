#!/usr/bin/env bash

if [ ! -d "inbox" ]; then
    echo "Ошибка: папка inbox не найдена"
    exit 1
fi

python3 distribution_of_email.py .
