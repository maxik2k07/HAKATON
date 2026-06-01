import os
import shutil
import ssl
from string import punctuation

ssl._create_default_https_context = ssl._create_unverified_context

import nltk
from nltk.tokenize import TweetTokenizer
from nltk.corpus import stopwords
from nltk.stem.snowball import SnowballStemmer

nltk.download('stopwords', quiet=True)

class EmailReader:

    def search_for_sender(self, file):
        for line in file:
            if 'From' in line or 'from' in line or 'Ot kogo' in line or 'От кого' in line:
                words = line.split()
                for mail in words:
                    if '@' in mail:
                        if '<' in mail and '>' in mail:
                            return mail[1:-1]
                        else:
                            return mail

    def search_for_recipient(self, file):
        for line in file:
            if 'to' in line or 'Komu' in line or 'Кому' in line or 'To' in line:
                words = line.split()
                for mail in words:
                    if '@' in mail:
                        return mail
        return None

    def search_subject(self, file):
        k = 0
        for line in file:
            if 'Subject' in line or 'subject' in line:
                words = line.split()
                k += 1
            if k == 1:
                return line

    def search_text(self, file):
        text = ''
        sender = self.search_for_sender(file)
        recipient = self.search_for_recipient(file)
        for line in file:
            sender_valid = sender is None or sender not in line
            recipient_valid = recipient is None or recipient not in line
            if sender_valid and recipient_valid:
                text += f'{line}'
        return text

class EmailClassifier:

    def __init__(self):
        self.st = SnowballStemmer('russian')
        self.categories_weights = {
            'Спам': {
                'вложен': 0.03, 'выигра': 0.10, 'приз': 0.10, 'iphone': 0.09,
                'exclusive': 0.09, 'offer': 0.07, 'limited': 0.05, 'личност': 0.05,
                'заблокирова': 0.07, 'перейд': 0.07, 'ссылк': 0.05, 'password-reset': 0.05,
                'secure-login': 0.05, 'внешн': 0.05, 'парол': 0.01,
                'эксклюзивн': 0.04, 'акц': 0.03
            },
            'Важное': {
                'urgent': 0.12, 'срочн': 0.12, 'критическ': 0.12, 'массов': 0.09,
                'сбо': 0.12, 'работ': 0.08, 'остановл': 0.09, 'отвеча': 0.08,
                'недоступ': 0.08, 'утечк': 0.05, 'дан': 0.02, 'краж': 0.03
            },
            'Технические ошибки': {
                'ошибк': 0.07, 'error': 0.03, 'зависа': 0.08,
                'слома': 0.08, 'ddos': 0.05, 'ремонт': 0.05, 'перебо': 0.05,
                'интернет': 0.04, 'связ': 0.04, 'запуска': 0.04, 'обновлен': 0.04,
                'открыва': 0.03, 'компьютер': 0.03, 'ноутбук': 0.03, 'принтер': 0.03,
                'сканер': 0.03, 'outlook': 0.03, 'chrome': 0.03, 'excel': 0.03,
                'zoom': 0.03, 'мыш': 0.03,
                'гарнитур': 0.02, 'неисправн': 0.04,
                'подключ': 0.04, 'кнопк': 0.02, 'портал': 0.01
            },
            'Информация': {
                'созвон': 0.15, 'дайджест': 0.11, 'мониторинг': 0.11, 'healthcheck': 0.11,
                'дем': 0.11, 'отчет': 0.08, 'info': 0.08, 'планов': 0.06,
                'брифинг': 0.06, 'брейншторм': 0.05, 'обновлен': 0.04, 'встреч': 0.02,
                'работ': 0.02
            },
            'Документы': {
                'договор': 0.12, 'акт': 0.10, 'закрыва': 0.13, 'документ': 0.13,
                'согласован': 0.13, 'contract': 0.13, 'финальн': 0.10, 'верс': 0.03,
                'дан': 0.03, 'задан': 0.01, 'задание': 0.05, 'инструкц': 0.02, 'инструкция': 0.02
            },
            'Счета': {
                'счет': 0.25, 'оплат': 0.25, 'invoice': 0.15, 'реквизит': 0.10,
                'задолжен': 0.03, 'акт': 0.03, 'выписк': 0.03, 'кред': 0.03,
                'выплат': 0.03, 'бухгалтер': 0.03, 'страховк': 0.03, 'зарплат': 0.02,
                'прем': 0.01, 'компенсац': 0.01
            },
            'Подтверждение доступа к аккаунту': {
                'vpn': 0.12, 'gitlab': 0.12, 'confluence': 0.12, '1c': 0.12,
                'выда': 0.09, 'прав': 0.09, 'восстанов': 0.08, 'запрос': 0.07,
                'доступ': 0.07, 'логин': 0.05, 'аккаунт': 0.04, 'почт': 0.02,
                'парол': 0.01
            },
            'HR': {
                'отпуск': 0.10, 'больничн': 0.10, 'резюм': 0.09, 'оформлен': 0.08,
                'должност': 0.07, 'назначен': 0.07, 'повышен': 0.07, 'отпускн': 0.07,
                'опоздан': 0.07, 'нетрудоспособн': 0.07, 'график': 0.05, 'сотрудник': 0.04,
                'работ': 0.02, 'перевод': 0.05, 'отдел': 0.05
            }
        }

    def tokenizer(self, t):
        t = t.lower()
        tokeniz = TweetTokenizer()
        tokeny = tokeniz.tokenize(t)
        tokeny = [tok for tok in tokeny if (tok not in stopwords.words('russian')) and (tok not in punctuation)]
        return tokeny

    def classify_email(self, text):
        if not text or len(text) == 0:
            return 'Спам'

        tokens = self.tokenizer(text)

        if len(tokens) == 0:
            return 'Спам'

        scores = {category: 0.0 for category in self.categories_weights.keys()}

        for token in tokens:
            stemmed = self.st.stem(token)
            for category, words_weights in self.categories_weights.items():
                if stemmed in words_weights:
                    scores[category] += words_weights[stemmed]

        THRESHOLD = 0.05

        if max(scores.values()) < THRESHOLD:
            return 'Не распределено'

        return max(scores, key=scores.get)

class EmailProcessor:

    def __init__(self, inbox_dir='inbox'):
        self.inbox_dir = inbox_dir
        self.reader = EmailReader()
        self.classifier = EmailClassifier()

    def process_all(self):
        results = []
        files = sorted(os.listdir(self.inbox_dir))

        for file_name in files:
            full_path = os.path.join(self.inbox_dir, file_name)

            if file_name.lower().endswith(('.jpeg', '.jpg', '.png')):
                results.append({'file': file_name, 'category': 'Картинки'})
                continue

            ext = os.path.splitext(file_name)[1].lower()
            if ext not in ('', '.txt'):
                results.append({'file': file_name, 'category': 'Ошибки'})
                continue

            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
            except (UnicodeDecodeError, OSError):
                results.append({'file': file_name, 'category': 'Ошибки'})
                continue

            has_sender = False
            has_recipient = False
            clean_lines = []

            for line in lines:
                ll = line.lower()
                if ('from:' in ll or 'от кого:' in ll or 'ot kogo:' in ll) and '@' in line:
                    has_sender = True
                    continue
                if ('to:' in ll or 'кому:' in ll or 'komu:' in ll) and '@' in line:
                    has_recipient = True
                    continue
                if 'date:' in ll or 'дата:' in ll:
                    continue
                clean_lines.append(line)

            if not has_sender:
                results.append({'file': file_name, 'category': 'Ошибки'})
                continue
            if not has_recipient:
                results.append({'file': file_name, 'category': 'Черновик'})
                continue

            email_text = ''.join(clean_lines).strip()
            category = self.classifier.classify_email(email_text)
            results.append({'file': file_name, 'category': category})

        txt_categories = {
            os.path.splitext(r['file'])[0]: r['category']
            for r in results
            if r['file'].lower().endswith('.txt')
        }
        for r in results:
            if r['category'] == 'Картинки':
                base = os.path.splitext(r['file'])[0]
                if base in txt_categories:
                    r['category'] = txt_categories[base]

        return results

class EmailSorter:

    def __init__(self, inbox_dir='inbox', output_dir='processed'):
        self.inbox_dir = inbox_dir
        self.output_dir = output_dir

    def sort(self, results):
        for item in results:
            src = os.path.join(self.inbox_dir, item['file'])
            dst_dir = os.path.join(self.output_dir, item['category'])
            os.makedirs(dst_dir, exist_ok=True)
            shutil.move(src, os.path.join(dst_dir, item['file']))

CATEGORIES = [
    'Важное',
    'Технические ошибки',
    'Подтверждение доступа к аккаунту',
    'Информация',
    'Документы',
    'Счета',
    'HR',
    'Спам',
]

def interactive_sort(undetermined, processed_dir):
    if not undetermined:
        return

    print(f"\nНераспознанных писем: {len(undetermined)}\n")

    reader = EmailReader()

    for i, item in enumerate(undetermined, 1):
        src = os.path.join(processed_dir, 'Не распределено', item['file'])

        ext = os.path.splitext(item['file'])[1] or '(без расширения)'
        print(f"\n[{i}/{len(undetermined)}] {item['file']}")
        print(f"  Формат:      {ext}")

        try:
            with open(src, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            sender = reader.search_for_sender(lines) or '—'
            subject = reader.search_subject(lines)
            subject = subject.strip() if subject else '—'
            preview = ''.join(lines[:3]).strip()
        except Exception:
            sender, subject, preview = '—', '—', '(не удалось прочитать)'

        print(f"  Отправитель: {sender}")
        print(f"  Тема:        {subject}")
        print(f"  Текст:       {preview[:120]}")
        print()

        for j, cat in enumerate(CATEGORIES, 1):
            print(f"  {j}. {cat}")
        print(f"  0. Пропустить")

        while True:
            choice = input("\n> ").strip()
            if choice == '0':
                print("  Пропущено.")
                break
            if choice.isdigit() and 1 <= int(choice) <= len(CATEGORIES):
                chosen = CATEGORIES[int(choice) - 1]
                dst_dir = os.path.join(processed_dir, chosen)
                os.makedirs(dst_dir, exist_ok=True)
                shutil.move(src, os.path.join(dst_dir, item['file']))
                print(f"  Перемещено -> {chosen}/")
                break
            print(f"  Введите число от 0 до {len(CATEGORIES)}")

if __name__ == '__main__':
    import sys
    from collections import Counter


    if len(sys.argv) > 1:
        project_path = sys.argv[1]
    else:
        project_path = '.'

    inbox_dir = os.path.join(project_path, 'inbox')
    processed_dir = os.path.join(project_path, 'processed')

    processor = EmailProcessor(inbox_dir)
    results = processor.process_all()

    sorter = EmailSorter(inbox_dir, processed_dir)
    sorter.sort(results)

    undetermined = [r for r in results if r['category'] == 'Не распределено']
    interactive_sort(undetermined, processed_dir)

    for item in results:
        if item['category'] == 'Не распределено':
            for cat in CATEGORIES:
                if os.path.exists(os.path.join(processed_dir, cat, item['file'])):
                    item['category'] = cat
                    break

    counts = Counter(r['category'] for r in results)
    print("\nРаспределение писем:\n")
    for item in results:
        print(f"  {item['file']:30s}  {item['category']}")

    print(f"\nПапки в {processed_dir}:\n")
    for cat, n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {n:3d}  {cat}/")
    print()

    from datetime import datetime
    log_path = os.path.join(processed_dir, 'log.txt')
    with open(log_path, 'w', encoding='utf-8') as log:
        log.write(f"Дата запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log.write(f"Всего писем: {len(results)}\n\n")
        for item in results:
            log.write(f"{item['file']:30s}  {item['category']}\n")
    print(f"Лог сохранён: {log_path}\n")
