# Moving Features Between Objects

Refactorings for moving functionality between classes and creating new classes.

## Move Method

**Description**: Move a method to the class that uses it most.

**When to use**:
- A method uses more features of another class than its own
- A method is used more by another class
- Planning to move several methods and this is part of that process

**Syntax**:
```bash
molting move-method <source> --to <target_class>
```

**Example**:

Before:
```python
# account.py
class Account:
    def __init__(self, account_type):
        self.account_type = account_type
        self.days_overdrawn = 0

    def overdraft_charge(self):
        if self.account_type.is_premium():
            result = 10
            if self.days_overdrawn > 7:
                result += (self.days_overdrawn - 7) * 0.85
            return result
        else:
            return self.days_overdrawn * 1.75

# account_type.py
class AccountType:
    def is_premium(self):
        # implementation
        pass
```

Command:
```bash
molting move-method account.py::Account::overdraft_charge --to AccountType
```

After:
```python
# account.py
class Account:
    def __init__(self, account_type):
        self.account_type = account_type
        self.days_overdrawn = 0

    def overdraft_charge(self):
        return self.account_type.overdraft_charge(self.days_overdrawn)

# account_type.py
class AccountType:
    def is_premium(self):
        # implementation
        pass

    def overdraft_charge(self, days_overdrawn):
        if self.is_premium():
            result = 10
            if days_overdrawn > 7:
                result += (days_overdrawn - 7) * 0.85
            return result
        else:
            return days_overdrawn * 1.75
```

---

## Move Field

**Description**: Move a field to the class that uses it most.

**When to use**:
- A field is used more by another class
- Planning Extract Class and want to move field first
- Doing other refactorings that would be helped by moving field

**Syntax**:
```bash
molting move-field <source> --to <target_class>
```

**Example**:

Before:
```python
class Account:
    def __init__(self):
        self.interest_rate = 0.05

    def interest_for_days(self, days):
        return self.interest_rate * days

class AccountType:
    pass
```

Command:
```bash
molting move-field account.py::Account::interest_rate --to AccountType
```

After:
```python
class Account:
    def __init__(self, account_type):
        self.account_type = account_type

    def interest_for_days(self, days):
        return self.account_type.interest_rate * days

class AccountType:
    def __init__(self):
        self.interest_rate = 0.05
```

---

## Extract Class

**Description**: Create a new class and move relevant fields and methods into it.

**When to use**:
- A class is doing the work of two
- Subsets of methods and data go together
- Class is too large to understand easily

**Syntax**:
```bash
molting extract-class <source> --fields <field1,field2> --methods <method1,method2> --name <NewClassName>
```

**Example**:

Before:
```python
class Person:
    def __init__(self, name, office_area_code, office_number):
        self.name = name
        self.office_area_code = office_area_code
        self.office_number = office_number

    def get_telephone_number(self):
        return f"({self.office_area_code}) {self.office_number}"
```

Command:
```bash
molting extract-class person.py::Person \
  --fields office_area_code,office_number \
  --methods get_telephone_number \
  --name TelephoneNumber
```

After:
```python
class Person:
    def __init__(self, name, office_area_code, office_number):
        self.name = name
        self.office_telephone = TelephoneNumber(office_area_code, office_number)

    def get_telephone_number(self):
        return self.office_telephone.get_telephone_number()

class TelephoneNumber:
    def __init__(self, area_code, number):
        self.area_code = area_code
        self.number = number

    def get_telephone_number(self):
        return f"({self.area_code}) {self.number}"
```

---

## Inline Class

**Description**: Move all features from one class into another and delete the first class.

**When to use**:
- A class is no longer doing much
- Want to collapse a hierarchy
- Have two classes and want to redistribute responsibilities by merging them

**Syntax**:
```bash
molting inline-class <source_class> --into <target_class>
```

**Example**:

Before:
```python
class Person:
    def __init__(self, name):
        self.name = name
        self.office_telephone = TelephoneNumber()

    def get_telephone_number(self):
        return self.office_telephone.get_telephone_number()

class TelephoneNumber:
    def __init__(self):
        self.area_code = ""
        self.number = ""

    def get_telephone_number(self):
        return f"({self.area_code}) {self.number}"
```

Command:
```bash
molting inline-class telephone.py::TelephoneNumber --into Person
```

After:
```python
class Person:
    def __init__(self, name):
        self.name = name
        self.office_area_code = ""
        self.office_number = ""

    def get_telephone_number(self):
        return f"({self.office_area_code}) {self.office_number}"
```

---

## Hide Delegate

**Description**: Create methods on the server to hide the delegate.

**When to use**:
- Client is calling a delegate class of an object
- Want to remove dependency between client and delegate
- Following Law of Demeter

**Syntax**:
```bash
molting hide-delegate <target>::<delegate_field>
```

**Example**:

Before:
```python
# Client code
manager = employee.department.manager

# Classes
class Person:
    def __init__(self, department):
        self.department = department

class Department:
    def __init__(self, manager):
        self.manager = manager
```

Command:
```bash
molting hide-delegate person.py::Person::department
```

After:
```python
# Client code
manager = employee.get_manager()

# Classes
class Person:
    def __init__(self, department):
        self._department = department

    def get_manager(self):
        return self._department.manager

class Department:
    def __init__(self, manager):
        self.manager = manager
```

---

## Remove Middle Man

**Description**: Get the client to call the delegate directly.

**When to use**:
- Class is doing too much simple delegation
- Half the methods are simple delegations
- Want to work with the delegate class directly

**Syntax**:
```bash
molting remove-middle-man <target>
```

**Example**:

Before:
```python
# Client code
manager = employee.get_manager()

# Classes
class Person:
    def __init__(self, department):
        self._department = department

    def get_manager(self):
        return self._department.manager

class Department:
    def __init__(self, manager):
        self.manager = manager
```

Command:
```bash
molting remove-middle-man person.py::Person
```

After:
```python
# Client code
manager = employee.department.manager

# Classes
class Person:
    def __init__(self, department):
        self.department = department

class Department:
    def __init__(self, manager):
        self.manager = manager
```

---

## Introduce Foreign Method

**Description**: Create a method in the client class with an instance of the server class as its first argument.

**When to use**:
- Server class needs an additional method but you can't modify it
- Need only one or two methods (otherwise use Introduce Local Extension)
- Using a library class that you can't change

**Syntax**:
```bash
molting introduce-foreign-method <target>#L<line> --for <class_name> --name <method_name>
```

**Example**:

Before:
```python
from datetime import date

class Report:
    def generate(self):
        # Need next day but date doesn't have a convenient method
        previous_end = date(2023, 5, 31)
        new_start = date(previous_end.year, previous_end.month, previous_end.day + 1)
```

Command:
```bash
molting introduce-foreign-method report.py::Report::generate#L6 --for date --name next_day
```

After:
```python
from datetime import date, timedelta

class Report:
    def generate(self):
        previous_end = date(2023, 5, 31)
        new_start = self.next_day(previous_end)

    def next_day(self, arg):
        # Foreign method for date
        return arg + timedelta(days=1)
```

---

## Introduce Local Extension

**Description**: Create a new class that contains the extra methods, make it a subclass or wrapper of the original.

**When to use**:
- Server class needs several additional methods
- Can't modify the server class
- Want to add substantial behavior

**Syntax**:
```bash
molting introduce-local-extension <target_class> --name <extension_class> --type <subclass|wrapper>
```

**Example**:

Before:
```python
from datetime import date

# Client code scattered with date calculations
new_start = date(previous_end.year, previous_end.month, previous_end.day + 1)
```

Command:
```bash
molting introduce-local-extension date --name MfDate --type subclass
```

After:
```python
from datetime import date, timedelta

class MfDate(date):
    def next_day(self):
        return self + timedelta(days=1)

    def days_after(self, days):
        return self + timedelta(days=days)

# Client code
new_start = previous_end.next_day()
```
