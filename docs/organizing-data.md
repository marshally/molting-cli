# Organizing Data

Refactorings for organizing data structures, encapsulation, and replacing primitives with objects.

## Self Encapsulate Field

**Description**: Create getting and setting methods for a field and use only those to access the field.

**When to use**:
- Want to add behavior when getting/setting a field
- Need lazy initialization
- Subclasses need to override field access

**Syntax**:
```bash
molting self-encapsulate-field <target>::<field_name>
```

**Example**:

Before:
```python
class Range:
    def __init__(self, low, high):
        self.low = low
        self.high = high

    def includes(self, arg):
        return arg >= self.low and arg <= self.high
```

Command:
```bash
molting self-encapsulate-field range.py::Range::low
molting self-encapsulate-field range.py::Range::high
```

After:
```python
class Range:
    def __init__(self, low, high):
        self._low = low
        self._high = high

    @property
    def low(self):
        return self._low

    @low.setter
    def low(self, value):
        self._low = value

    @property
    def high(self):
        return self._high

    @high.setter
    def high(self, value):
        self._high = value

    def includes(self, arg):
        return arg >= self.low and arg <= self.high
```

---

## Replace Data Value with Object

**Description**: Turn a data item into an object.

**When to use**:
- Data item needs additional data or behavior
- Have duplicated data and logic
- Simple data becomes complex as development proceeds

**Syntax**:
```bash
molting replace-data-value-with-object <target>::<field_name> --name <new_class_name>
```

**Example**:

Before:
```python
class Order:
    def __init__(self, customer_name):
        self.customer = customer_name

    def get_customer_name(self):
        return self.customer
```

Command:
```bash
molting replace-data-value-with-object order.py::Order::customer --name Customer
```

After:
```python
class Order:
    def __init__(self, customer_name):
        self.customer = Customer(customer_name)

    def get_customer_name(self):
        return self.customer.name

class Customer:
    def __init__(self, name):
        self.name = name
```

---

## Change Value to Reference

**Description**: Turn a value object into a reference object.

**When to use**:
- Have many equal instances that you want to replace with a single object
- Want to centralize updates
- Object represents a real-world entity that should be unique

**Syntax**:
```bash
molting change-value-to-reference <target_class>
```

**Example**:

Before:
```python
class Order:
    def __init__(self, customer_name):
        self.customer = Customer(customer_name)

class Customer:
    def __init__(self, name):
        self.name = name
```

Command:
```bash
molting change-value-to-reference customer.py::Customer
```

After:
```python
class Order:
    def __init__(self, customer_name):
        self.customer = Customer.get_named(customer_name)

class Customer:
    _instances = {}

    def __init__(self, name):
        self.name = name

    @classmethod
    def get_named(cls, name):
        if name not in cls._instances:
            cls._instances[name] = Customer(name)
        return cls._instances[name]
```

---

## Change Reference to Value

**Description**: Turn a reference object into a value object.

**When to use**:
- Reference object is small and immutable
- Reference object is becoming awkward to manage
- Want to distribute object across processes or systems

**Syntax**:
```bash
molting change-reference-to-value <target_class>
```

**Example**:

Before:
```python
class Currency:
    _instances = {}

    def __init__(self, code):
        self.code = code

    @classmethod
    def get(cls, code):
        if code not in cls._instances:
            cls._instances[code] = Currency(code)
        return cls._instances[code]
```

Command:
```bash
molting change-reference-to-value currency.py::Currency
```

After:
```python
class Currency:
    def __init__(self, code):
        self.code = code

    def __eq__(self, other):
        if not isinstance(other, Currency):
            return False
        return self.code == other.code

    def __hash__(self):
        return hash(self.code)
```

---

## Replace Array with Object

**Description**: Replace an array with an object that has a field for each element.

**When to use**:
- Array elements have different meanings
- Using array indexes is confusing
- Want type safety and clarity

**Syntax**:
```bash
molting replace-array-with-object <target>::<array_field> --name <new_class_name>
```

**Example**:

Before:
```python
def analyze_performance(row):
    name = row[0]
    wins = row[1]
    losses = row[2]
    # process data
```

Command:
```bash
molting replace-array-with-object performance.py::analyze_performance::row --name Performance
```

After:
```python
class Performance:
    def __init__(self, name, wins, losses):
        self.name = name
        self.wins = wins
        self.losses = losses

def analyze_performance(performance):
    name = performance.name
    wins = performance.wins
    losses = performance.losses
    # process data
```

---

## Duplicate Observed Data

**Description**: Copy data from domain object to GUI object and set up observer pattern.

**When to use**:
- Domain data is stored in GUI components
- Want to separate business logic from presentation
- Need to support multiple views of the same data

**Syntax**:
```bash
molting duplicate-observed-data <gui_class>::<field_name> --domain <domain_class>
```

**Example**:

Before:
```python
class IntervalWindow:
    def __init__(self):
        self.start_field = ""
        self.end_field = ""
        self.length_field = ""

    def start_field_focus_lost(self):
        self.calculate_length()

    def calculate_length(self):
        start = int(self.start_field)
        end = int(self.end_field)
        length = end - start
        self.length_field = str(length)
```

Command:
```bash
molting duplicate-observed-data interval_window.py::IntervalWindow::start_field --domain Interval
```

After:
```python
class IntervalWindow:
    def __init__(self):
        self.interval = Interval()
        self.start_field = ""
        self.end_field = ""
        self.length_field = ""
        self.update()

    def start_field_focus_lost(self):
        self.interval.start = int(self.start_field)
        self.calculate_length()

    def calculate_length(self):
        self.interval.calculate_length()
        self.update()

    def update(self):
        self.start_field = str(self.interval.start)
        self.end_field = str(self.interval.end)
        self.length_field = str(self.interval.length)

class Interval:
    def __init__(self):
        self.start = 0
        self.end = 0
        self.length = 0

    def calculate_length(self):
        self.length = self.end - self.start
```

---

## Change Unidirectional Association to Bidirectional

**Description**: Add back pointers and change modifiers to update both sets.

**When to use**:
- Two classes need to use each other's features
- Client needs to navigate both directions
- Want to avoid duplicate code by centralizing logic

**Syntax**:
```bash
molting change-unidirectional-association-to-bidirectional <source>::<field> --back <back_field>
```

**Example**:

Before:
```python
class Order:
    def __init__(self, customer):
        self.customer = customer

class Customer:
    pass
```

Command:
```bash
molting change-unidirectional-association-to-bidirectional order.py::Order::customer --back orders
```

After:
```python
class Order:
    def __init__(self, customer):
        self._customer = None
        self.set_customer(customer)

    def set_customer(self, customer):
        if self._customer is not None:
            self._customer.remove_order(self)
        self._customer = customer
        if customer is not None:
            customer.add_order(self)

class Customer:
    def __init__(self):
        self._orders = set()

    def add_order(self, order):
        self._orders.add(order)

    def remove_order(self, order):
        self._orders.discard(order)
```

---

## Change Bidirectional Association to Unidirectional

**Description**: Remove back pointers.

**When to use**:
- Bidirectional association is no longer needed
- Want to reduce coupling
- One direction is causing maintenance problems

**Syntax**:
```bash
molting change-bidirectional-association-to-unidirectional <source>::<field_to_remove>
```

**Example**:

Before:
```python
class Order:
    def __init__(self, customer):
        self._customer = None
        self.set_customer(customer)

    def set_customer(self, customer):
        if self._customer is not None:
            self._customer.remove_order(self)
        self._customer = customer
        if customer is not None:
            customer.add_order(self)

class Customer:
    def __init__(self):
        self._orders = set()

    def add_order(self, order):
        self._orders.add(order)

    def remove_order(self, order):
        self._orders.discard(order)
```

Command:
```bash
molting change-bidirectional-association-to-unidirectional customer.py::Customer::_orders
```

After:
```python
class Order:
    def __init__(self, customer):
        self.customer = customer

class Customer:
    pass
```

---

## Replace Magic Number with Symbolic Constant

**Description**: Create a constant, name it after the meaning, and replace the number with it.

**When to use**:
- Have a literal number with a particular meaning
- Number appears in multiple places
- Want to make code self-documenting

**Syntax**:
```bash
molting replace-magic-number-with-symbolic-constant <target>#L<line> --name <constant_name>
```

**Example**:

Before:
```python
def potential_energy(mass, height):
    return mass * 9.81 * height
```

Command:
```bash
molting replace-magic-number-with-symbolic-constant physics.py::potential_energy#L2 --name GRAVITATIONAL_CONSTANT
```

After:
```python
GRAVITATIONAL_CONSTANT = 9.81

def potential_energy(mass, height):
    return mass * GRAVITATIONAL_CONSTANT * height
```

---

## Encapsulate Field

**Description**: Make the field private and provide accessors.

**When to use**:
- Have a public field
- Want to control access to the field
- Need to add behavior when field is accessed or changed

**Syntax**:
```bash
molting encapsulate-field <target>::<field_name>
```

**Example**:

Before:
```python
class Person:
    def __init__(self, name):
        self.name = name
```

Command:
```bash
molting encapsulate-field person.py::Person::name
```

After:
```python
class Person:
    def __init__(self, name):
        self._name = name

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value
```

---

## Encapsulate Collection

**Description**: Make the method return a read-only view and provide add/remove methods.

**When to use**:
- Method returns a collection
- Want to control how collection is modified
- Need to maintain invariants when collection changes

**Syntax**:
```bash
molting encapsulate-collection <target>::<collection_field>
```

**Example**:

Before:
```python
class Person:
    def __init__(self):
        self.courses = []

    def get_courses(self):
        return self.courses
```

Command:
```bash
molting encapsulate-collection person.py::Person::courses
```

After:
```python
class Person:
    def __init__(self):
        self._courses = []

    def get_courses(self):
        return tuple(self._courses)  # Read-only view

    def add_course(self, course):
        self._courses.append(course)

    def remove_course(self, course):
        self._courses.remove(course)
```

---

## Replace Type Code with Class

**Description**: Replace the type code with a new class.

**When to use**:
- Have type codes that don't affect behavior
- Want type safety
- Type code is not used in conditionals

**Syntax**:
```bash
molting replace-type-code-with-class <target>::<type_field> --name <new_class_name>
```

**Example**:

Before:
```python
class Person:
    O = 0
    A = 1
    B = 2
    AB = 3

    def __init__(self, blood_group):
        self.blood_group = blood_group
```

Command:
```bash
molting replace-type-code-with-class person.py::Person::blood_group --name BloodGroup
```

After:
```python
class BloodGroup:
    O = BloodGroup(0)
    A = BloodGroup(1)
    B = BloodGroup(2)
    AB = BloodGroup(3)

    def __init__(self, code):
        self._code = code

class Person:
    def __init__(self, blood_group):
        self.blood_group = blood_group
```

---

## Replace Type Code with Subclasses

**Description**: Replace the type code with subclasses.

**When to use**:
- Have type code that affects behavior
- Want to use polymorphism
- Type code is immutable

**Syntax**:
```bash
molting replace-type-code-with-subclasses <target>::<type_field>
```

**Example**:

Before:
```python
class Employee:
    ENGINEER = 0
    SALESMAN = 1
    MANAGER = 2

    def __init__(self, employee_type):
        self.type = employee_type
```

Command:
```bash
molting replace-type-code-with-subclasses employee.py::Employee::type
```

After:
```python
class Employee:
    @staticmethod
    def create(employee_type):
        if employee_type == "ENGINEER":
            return Engineer()
        elif employee_type == "SALESMAN":
            return Salesman()
        elif employee_type == "MANAGER":
            return Manager()

class Engineer(Employee):
    pass

class Salesman(Employee):
    pass

class Manager(Employee):
    pass
```

---

## Replace Type Code with State/Strategy

**Description**: Replace the type code with a state object.

**When to use**:
- Have type code that affects behavior
- Type code changes during object's lifetime
- Want to use polymorphism

**Syntax**:
```bash
molting replace-type-code-with-state-strategy <target>::<type_field> --name <state_class_name>
```

**Example**:

Before:
```python
class Employee:
    ENGINEER = 0
    SALESMAN = 1
    MANAGER = 2

    def __init__(self, employee_type):
        self.type = employee_type

    def pay_amount(self):
        if self.type == self.ENGINEER:
            return self.monthly_salary
        elif self.type == self.SALESMAN:
            return self.monthly_salary + self.commission
        elif self.type == self.MANAGER:
            return self.monthly_salary + self.bonus
```

Command:
```bash
molting replace-type-code-with-state-strategy employee.py::Employee::type --name EmployeeType
```

After:
```python
class Employee:
    def __init__(self, employee_type):
        self.type = employee_type

    def pay_amount(self):
        return self.type.pay_amount(self)

class EmployeeType:
    def pay_amount(self, employee):
        raise NotImplementedError

class Engineer(EmployeeType):
    def pay_amount(self, employee):
        return employee.monthly_salary

class Salesman(EmployeeType):
    def pay_amount(self, employee):
        return employee.monthly_salary + employee.commission

class Manager(EmployeeType):
    def pay_amount(self, employee):
        return employee.monthly_salary + employee.bonus
```
