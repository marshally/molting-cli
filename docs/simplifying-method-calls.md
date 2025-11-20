# Simplifying Method Calls

Refactorings for making method interfaces clearer and easier to use.

## Rename Method

**Description**: Change the name of a method to better reveal its purpose.

**When to use**:
- Method name doesn't reveal its purpose
- Name is misleading or confusing
- Better name becomes apparent as code evolves

**Syntax**:
```bash
molting rename-method <target> <new_name>
```

**Example**:

Before:
```python
class Customer:
    def get_inv_cdtlmt(self):
        return self.invoice_credit_limit
```

Command:
```bash
molting rename-method customer.py::Customer::get_inv_cdtlmt get_invoice_credit_limit
```

After:
```python
class Customer:
    def get_invoice_credit_limit(self):
        return self.invoice_credit_limit
```

---

## Add Parameter

**Description**: Add a parameter for information needed by the method.

**When to use**:
- Method needs more information from its caller
- Want to make method more flexible
- Removing a dependency requires passing data instead

**Syntax**:
```bash
molting add-parameter <target> --name <param_name> --default <default_value>
```

**Example**:

Before:
```python
class Contact:
    def get_contact_info(self):
        return f"{self.name}\n{self.phone}"
```

Command:
```bash
molting add-parameter contact.py::Contact::get_contact_info --name include_email --default False
```

After:
```python
class Contact:
    def get_contact_info(self, include_email=False):
        result = f"{self.name}\n{self.phone}"
        if include_email:
            result += f"\n{self.email}"
        return result
```

---

## Remove Parameter

**Description**: Remove a parameter that is no longer used.

**When to use**:
- Parameter is no longer used
- Parameter is not needed
- Want to simplify method signature

**Syntax**:
```bash
molting remove-parameter <target>::<param_name>
```

**Example**:

Before:
```python
class Order:
    def calculate_total(self, customer, discount_code):
        # discount_code is never used
        return self.base_price * self.quantity
```

Command:
```bash
molting remove-parameter order.py::Order::calculate_total::discount_code
```

After:
```python
class Order:
    def calculate_total(self, customer):
        return self.base_price * self.quantity
```

---

## Separate Query from Modifier

**Description**: Create two methods, one for the query and one for the modification.

**When to use**:
- Method returns a value and also changes object state
- Want to eliminate side effects from queries
- Following Command-Query Separation principle

**Syntax**:
```bash
molting separate-query-from-modifier <target>
```

**Example**:

Before:
```python
class Security:
    def get_and_remove_intruder(self):
        if len(self.intruders) > 0:
            intruder = self.intruders[0]
            self.intruders.pop(0)
            return intruder
        return None
```

Command:
```bash
molting separate-query-from-modifier security.py::Security::get_and_remove_intruder
```

After:
```python
class Security:
    def get_intruder(self):
        if len(self.intruders) > 0:
            return self.intruders[0]
        return None

    def remove_intruder(self):
        if len(self.intruders) > 0:
            self.intruders.pop(0)
```

---

## Parameterize Method

**Description**: Create one method that uses a parameter for the different values.

**When to use**:
- Several methods do similar things with different values
- Methods differ only in some constant value
- Want to reduce duplication

**Syntax**:
```bash
molting parameterize-method <target1> <target2> --name <new_method_name>
```

**Example**:

Before:
```python
class Employee:
    def five_percent_raise(self):
        self.salary *= 1.05

    def ten_percent_raise(self):
        self.salary *= 1.10
```

Command:
```bash
molting parameterize-method employee.py::Employee::five_percent_raise employee.py::Employee::ten_percent_raise --name raise_salary
```

After:
```python
class Employee:
    def raise_salary(self, percentage):
        self.salary *= (1 + percentage / 100)

    def five_percent_raise(self):
        self.raise_salary(5)

    def ten_percent_raise(self):
        self.raise_salary(10)
```

---

## Replace Parameter with Explicit Methods

**Description**: Create a separate method for each value of the parameter.

**When to use**:
- Method runs different code based on parameter value
- Parameter values are from a fixed set
- Conditional logic based on parameter is getting complex

**Syntax**:
```bash
molting replace-parameter-with-explicit-methods <target>::<param_name>
```

**Example**:

Before:
```python
class Employee:
    HEIGHT = 0
    WIDTH = 1

    def set_value(self, name, value):
        if name == "height":
            self.height = value
        elif name == "width":
            self.width = value
```

Command:
```bash
molting replace-parameter-with-explicit-methods employee.py::Employee::set_value::name
```

After:
```python
class Employee:
    def set_height(self, value):
        self.height = value

    def set_width(self, value):
        self.width = value
```

---

## Preserve Whole Object

**Description**: Send the whole object instead of extracting values from it.

**When to use**:
- Getting several values from an object to pass as parameters
- Method might need more data from the object later
- Want to reduce parameter list length

**Syntax**:
```bash
molting preserve-whole-object <target>
```

**Example**:

Before:
```python
def within_plan(plan, low, high):
    return low >= plan.low and high <= plan.high

# Client
low = days_temp_range.low
high = days_temp_range.high
is_within = within_plan(plan, low, high)
```

Command:
```bash
molting preserve-whole-object heating.py::within_plan
```

After:
```python
def within_plan(plan, temp_range):
    return temp_range.low >= plan.low and temp_range.high <= plan.high

# Client
is_within = within_plan(plan, days_temp_range)
```

---

## Replace Parameter with Method Call

**Description**: Remove the parameter and have the receiver call the method.

**When to use**:
- Object can get parameter value by calling a method
- Parameter is result of a method call in the caller
- Want to simplify parameter list

**Syntax**:
```bash
molting replace-parameter-with-method-call <target>::<param_name>
```

**Example**:

Before:
```python
class Order:
    def get_price(self):
        base_price = self.quantity * self.item_price
        discount_level = self.get_discount_level()
        return self.discounted_price(base_price, discount_level)

    def discounted_price(self, base_price, discount_level):
        if discount_level == 2:
            return base_price * 0.9
        return base_price * 0.95

    def get_discount_level(self):
        return 2 if self.quantity > 100 else 1
```

Command:
```bash
molting replace-parameter-with-method-call order.py::Order::discounted_price::discount_level
```

After:
```python
class Order:
    def get_price(self):
        base_price = self.quantity * self.item_price
        return self.discounted_price(base_price)

    def discounted_price(self, base_price):
        if self.get_discount_level() == 2:
            return base_price * 0.9
        return base_price * 0.95

    def get_discount_level(self):
        return 2 if self.quantity > 100 else 1
```

---

## Introduce Parameter Object

**Description**: Replace parameters with a parameter object.

**When to use**:
- Group of parameters naturally go together
- Same group appears in multiple methods
- Want to reduce parameter list length

**Syntax**:
```bash
molting introduce-parameter-object <target> --params <param1,param2,param3> --name <ObjectName>
```

**Example**:

Before:
```python
class Account:
    def add_charge(self, amount, charge_date):
        self.charges.append(Charge(amount, charge_date))

def flow_between(start_date, end_date, account):
    return sum(charge.amount for charge in account.charges
               if start_date <= charge.date <= end_date)
```

Command:
```bash
molting introduce-parameter-object flow.py::flow_between --params start_date,end_date --name DateRange
```

After:
```python
class DateRange:
    def __init__(self, start, end):
        self.start = start
        self.end = end

    def includes(self, date):
        return self.start <= date <= self.end

class Account:
    def add_charge(self, amount, charge_date):
        self.charges.append(Charge(amount, charge_date))

def flow_between(date_range, account):
    return sum(charge.amount for charge in account.charges
               if date_range.includes(charge.date))
```

---

## Remove Setting Method

**Description**: Make the field immutable by removing the setter.

**When to use**:
- Field should be set only at creation time
- Want to make object immutable
- Setter is never called after construction

**Syntax**:
```bash
molting remove-setting-method <target>::<field_name>
```

**Example**:

Before:
```python
class Account:
    def __init__(self, id):
        self._id = id

    def get_id(self):
        return self._id

    def set_id(self, id):
        self._id = id
```

Command:
```bash
molting remove-setting-method account.py::Account::_id
```

After:
```python
class Account:
    def __init__(self, id):
        self._id = id

    def get_id(self):
        return self._id
```

---

## Hide Method

**Description**: Make the method private.

**When to use**:
- Method is not used by other classes
- Want to reduce public interface
- Method is an implementation detail

**Syntax**:
```bash
molting hide-method <target>
```

**Example**:

Before:
```python
class Employee:
    def calculate_bonus(self):
        return self.base_salary * self.get_bonus_multiplier()

    def get_bonus_multiplier(self):
        # Only used internally
        return 0.1 if self.rating > 8 else 0.05
```

Command:
```bash
molting hide-method employee.py::Employee::get_bonus_multiplier
```

After:
```python
class Employee:
    def calculate_bonus(self):
        return self.base_salary * self._get_bonus_multiplier()

    def _get_bonus_multiplier(self):
        return 0.1 if self.rating > 8 else 0.05
```

---

## Replace Constructor with Factory Function

**Description**: Replace the constructor with a factory function.

**When to use**:
- Constructor does more than simple construction
- Need to return different types based on parameters
- Constructor name is not descriptive enough

**Syntax**:
```bash
molting replace-constructor-with-factory-function <target>
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
molting replace-constructor-with-factory-function employee.py::Employee::__init__
```

After:
```python
class Employee:
    def __init__(self, employee_type):
        self.type = employee_type

def create_employee(employee_type):
    if employee_type == "ENGINEER":
        return Engineer()
    elif employee_type == "SALESMAN":
        return Salesman()
    elif employee_type == "MANAGER":
        return Manager()
```

---

## Replace Error Code with Exception

**Description**: Throw an exception instead of returning an error code.

**When to use**:
- Method returns special code to indicate error
- Error handling clutters normal flow
- Want to separate error handling from normal logic

**Syntax**:
```bash
molting replace-error-code-with-exception <target>
```

**Example**:

Before:
```python
def withdraw(account, amount):
    if amount > account.balance:
        return -1  # Error code
    else:
        account.balance -= amount
        return 0  # Success
```

Command:
```bash
molting replace-error-code-with-exception banking.py::withdraw
```

After:
```python
def withdraw(account, amount):
    if amount > account.balance:
        raise ValueError("Amount exceeds balance")
    account.balance -= amount
```

---

## Replace Exception with Test

**Description**: Change the caller to test first instead of catching exception.

**When to use**:
- Exception is being used for conditional logic
- Caller can check condition first
- Exception handling hurts performance

**Syntax**:
```bash
molting replace-exception-with-test <target>
```

**Example**:

Before:
```python
def get_value_for_period(period_count, values):
    try:
        return values[period_count]
    except IndexError:
        return 0
```

Command:
```bash
molting replace-exception-with-test resource.py::get_value_for_period
```

After:
```python
def get_value_for_period(period_count, values):
    if period_count >= len(values):
        return 0
    return values[period_count]
```
