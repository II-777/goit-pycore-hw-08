import pickle
from collections import UserDict
from datetime import datetime, date, timedelta
from functools import wraps


def input_error(func):
    """Повертає повідомлення замість падіння програми на помилці вводу."""

    @wraps(func)
    def inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as error:
            message = str(error)
            if message in {
                "Phone number must contain exactly 10 digits.",
                "Phone number not found.",
                "Invalid date format. Use DD.MM.YYYY",
                "Name is a required field.",
            }:
                return message
            if func.__name__ == "add_birthday":
                return "Give me name and birthday please."
            if func.__name__ == "change_contact":
                return "Give me name, old phone and new phone please."
            return "Give me name and phone please."
        except (KeyError, AttributeError):
            return "Contact not found."
        except IndexError:
            return "Enter user name."

    return inner


def parse_input(user_input: str):
    """Ділить рядок на команду та аргументи. Команда не залежить від регістру."""
    cmd, *args = user_input.split()
    cmd = cmd.strip().lower()
    return cmd, *args


class Field:
    """Базове поле запису."""

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)


class Name(Field):
    """Обов'язкове ім'я контакту."""

    def __init__(self, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Name is a required field.")
        super().__init__(value.strip())


class Phone(Field):
    """Номер телефону з 10 цифр."""

    def __init__(self, value):
        if not isinstance(value, str) or not value.isdigit() or len(value) != 10:
            raise ValueError("Phone number must contain exactly 10 digits.")
        super().__init__(value)


class Birthday(Field):
    """Дата народження. value є рядком формату DD.MM.YYYY."""

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        try:
            datetime.strptime(value, "%d.%m.%Y")
        except (ValueError, TypeError):
            raise ValueError("Invalid date format. Use DD.MM.YYYY")
        self._value = value

    @property
    def data(self):
        return datetime.strptime(self.value, "%d.%m.%Y").date()


class Record:
    """Контакт: ім'я, список телефонів і один необов'язковий день народження."""

    def __init__(self, name):
        self.name = Name(name)
        self.phones = []
        self.birthday = None

    def add_phone(self, phone):
        """Додає номер. Некоректний номер завершує метод помилкою ValueError."""
        self.phones.append(Phone(phone))

    def remove_phone(self, phone):
        """Видаляє номер. Якщо його немає в записі, видає помилку ValueError."""
        found = self.find_phone(phone)
        if found is None:
            raise ValueError("Phone number not found.")
        self.phones.remove(found)

    def edit_phone(self, old_phone, new_phone):
        """Замінює старий номер на новий. Некоректні дані дають ValueError."""
        found = self.find_phone(old_phone)
        if found is None:
            raise ValueError("Phone number not found.")
        self.phones[self.phones.index(found)] = Phone(new_phone)

    def find_phone(self, phone):
        """Повертає об'єкт Phone або None, якщо номера немає."""
        for item in self.phones:
            if item.value == phone:
                return item
        return None

    def add_birthday(self, birthday):
        """Додає одну дату народження. Некоректна дата дає ValueError."""
        self.birthday = Birthday(birthday)

    def __str__(self):
        phones = "; ".join(p.value for p in self.phones)
        line = f"Contact name: {self.name.value}, phones: {phones}"
        if self.birthday:
            line += f", birthday: {self.birthday}"
        return line


class AddressBook(UserDict):
    """Книга контактів. Ключ: ім'я, значення: Record."""

    def add_record(self, record):
        """Додає запис до self.data."""
        self.data[record.name.value] = record

    def find(self, name):
        """Повертає Record за ім'ям або None, якщо запису немає."""
        return self.data.get(name)

    def delete(self, name):
        """Видаляє запис за ім'ям."""
        del self.data[name]

    @staticmethod
    def _next_workday(day: date) -> date:
        """Суботу і неділю переносить на найближчий понеділок."""
        if day.weekday() >= 5:
            return day + timedelta(days=7 - day.weekday())
        return day

    def get_upcoming_birthdays(self, days=7):
        """Повертає привітання на сьогодні і наступні 7 днів.

        Кожен елемент є словником з ключами name і birthday.
        Якщо день народження вихідний, birthday це найближчий понеділок.
        """
        today = date.today()
        upcoming = []
        for record in self.data.values():
            if record.birthday is None:
                continue
            birthday = record.birthday.data.replace(year=today.year)
            if birthday < today:
                birthday = record.birthday.data.replace(year=today.year + 1)
            if 0 <= (birthday - today).days <= days:
                congratulation = self._next_workday(birthday)
                upcoming.append({
                    "name": record.name.value,
                    "birthday": congratulation.strftime("%d.%m.%Y"),
                })
        upcoming.sort(key=lambda item: datetime.strptime(item["birthday"], "%d.%m.%Y").date())
        return upcoming

    def __str__(self):
        if not self.data:
            return "Address book is empty."
        return "\n".join(str(record) for record in self.data.values())


@input_error
def add_contact(args, book: AddressBook) -> str:
    """Додає контакт або ще один номер до наявного контакту."""
    name, phone, *_ = args
    record = book.find(name)
    message = "Contact updated."
    if record is None:
        record = Record(name)
        book.add_record(record)
        message = "Contact added."
    record.add_phone(phone)
    return message


@input_error
def change_contact(args, book: AddressBook) -> str:
    """Замінює старий номер наявного контакту на новий."""
    name, old_phone, new_phone = args
    record = book.find(name)
    record.edit_phone(old_phone, new_phone)
    return "Contact updated."


@input_error
def show_phone(args, book: AddressBook) -> str:
    """Повертає номери телефону за ім'ям."""
    name = args[0]
    record = book.find(name)
    if not record.phones:
        return "No phone number saved."
    return "; ".join(phone.value for phone in record.phones)


@input_error
def show_all(book: AddressBook) -> str:
    """Повертає всі збережені контакти."""
    if not book.data:
        return "No contacts saved."
    return str(book)


@input_error
def add_birthday(args, book: AddressBook) -> str:
    """Додає день народження контакту у форматі DD.MM.YYYY."""
    name, birthday = args
    record = book.find(name)
    record.add_birthday(birthday)
    return "Birthday added."


@input_error
def show_birthday(args, book: AddressBook) -> str:
    """Повертає день народження контакту."""
    name = args[0]
    record = book.find(name)
    if record.birthday is None:
        return "Birthday not saved."
    return str(record.birthday)


@input_error
def birthdays(args, book: AddressBook) -> str:
    """Повертає дні народження на найближчі 7 днів."""
    upcoming = book.get_upcoming_birthdays()
    if not upcoming:
        return "No upcoming birthdays."
    return "\n".join(f"{item['name']}: {item['birthday']}" for item in upcoming)


def save_data(book, filename="addressbook.pkl"):
    """Зберігає адресну книгу у файл."""
    with open(filename, "wb") as file:
        pickle.dump(book, file)


def load_data(filename="addressbook.pkl"):
    """Відновлює адресну книгу з файлу. Якщо файлу немає, повертає порожню книгу."""
    try:
        with open(filename, "rb") as file:
            return pickle.load(file)
    except FileNotFoundError:
        return AddressBook()


def main():
    book = load_data()
    print("Welcome to the assistant bot!")
    while True:
        user_input = input("Enter a command: ")
        if not user_input.strip():
            print("Invalid command.")
            continue

        command, *args = parse_input(user_input)

        if command in ["close", "exit"]:
            print("Good bye!")
            break
        elif command == "hello":
            print("How can I help you?")
        elif command == "add":
            print(add_contact(args, book))
        elif command == "change":
            print(change_contact(args, book))
        elif command == "phone":
            print(show_phone(args, book))
        elif command == "all":
            print(show_all(book))
        elif command == "add-birthday":
            print(add_birthday(args, book))
        elif command == "show-birthday":
            print(show_birthday(args, book))
        elif command == "birthdays":
            print(birthdays(args, book))
        else:
            print("Invalid command.")

    save_data(book)


if __name__ == "__main__":
    main()
