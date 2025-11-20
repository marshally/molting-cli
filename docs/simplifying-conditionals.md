# Simplifying Conditional Expressions

Refactorings for making conditional logic clearer and more maintainable.

## Decompose Conditional

**Description**: Extract the condition and each branch into separate methods.

**When to use**:
- Complex conditional statement is hard to read
- Condition and branches are long
- Want to make the intent clear

**Syntax**:
```bash
molting decompose-conditional <target>#L<start>-L<end>
```

**Example**:

Before:
```python
def calculate_charge(quantity, date):
    if date.month < 6 or date.month > 8:
        charge = quantity * winter_rate + winter_service_charge
    else:
        charge = quantity * summer_rate
    return charge
```

Command:
```bash
molting decompose-conditional billing.py::calculate_charge#L2-L5
```

After:
```python
def calculate_charge(quantity, date):
    if is_winter(date):
        charge = winter_charge(quantity)
    else:
        charge = summer_charge(quantity)
    return charge

def is_winter(date):
    return date.month < 6 or date.month > 8

def winter_charge(quantity):
    return quantity * winter_rate + winter_service_charge

def summer_charge(quantity):
    return quantity * summer_rate
```

---

## Consolidate Conditional Expression

**Description**: Combine the sequence of conditional tests into a single condition and extract it.

**When to use**:
- Have several conditionals with the same result
- Checks are really the same thing
- Want to make the check clearer

**Syntax**:
```bash
molting consolidate-conditional-expression <target>#L<start>-L<end> --name <extracted_method>
```

**Example**:

Before:
```python
def disability_amount(employee):
    if employee.seniority < 2:
        return 0
    if employee.months_disabled > 12:
        return 0
    if employee.is_part_time:
        return 0
    # calculate disability amount
```

Command:
```bash
molting consolidate-conditional-expression employee.py::disability_amount#L2-L7 --name is_not_eligible_for_disability
```

After:
```python
def disability_amount(employee):
    if is_not_eligible_for_disability(employee):
        return 0
    # calculate disability amount

def is_not_eligible_for_disability(employee):
    return (employee.seniority < 2 or
            employee.months_disabled > 12 or
            employee.is_part_time)
```

---

## Consolidate Duplicate Conditional Fragments

**Description**: Move the duplicate code outside the conditional.

**When to use**:
- Same fragment of code in all branches of a conditional
- Want to remove duplication
- Code should execute regardless of condition

**Syntax**:
```bash
molting consolidate-duplicate-conditional-fragments <target>#L<start>-L<end>
```

**Example**:

Before:
```python
def process_order(is_special):
    if is_special:
        total = price * 0.95
        send_order()
    else:
        total = price * 0.98
        send_order()
```

Command:
```bash
molting consolidate-duplicate-conditional-fragments order.py::process_order#L2-L6
```

After:
```python
def process_order(is_special):
    if is_special:
        total = price * 0.95
    else:
        total = price * 0.98
    send_order()
```

---

## Remove Control Flag

**Description**: Use break or return instead of a variable acting as a control flag.

**When to use**:
- Using a variable as a control flag for a loop or conditional
- Control flag makes code harder to understand
- Can use break, continue, or return instead

**Syntax**:
```bash
molting remove-control-flag <target>::<flag_variable>
```

**Example**:

Before:
```python
def check_security(people):
    found = False
    for person in people:
        if not found:
            if person == "Don":
                send_alert()
                found = True
            if person == "John":
                send_alert()
                found = True
```

Command:
```bash
molting remove-control-flag security.py::check_security::found
```

After:
```python
def check_security(people):
    for person in people:
        if person == "Don":
            send_alert()
            return
        if person == "John":
            send_alert()
            return
```

---

## Replace Nested Conditional with Guard Clauses

**Description**: Use guard clauses for all special cases.

**When to use**:
- Conditional has special case behavior
- Normal path is buried in nested conditionals
- Want to emphasize error conditions

**Syntax**:
```bash
molting replace-nested-conditional-with-guard-clauses <target>#L<start>-L<end>
```

**Example**:

Before:
```python
def get_payment_amount(employee):
    if employee.is_separated:
        result = 0
    else:
        if employee.is_retired:
            result = 0
        else:
            if employee.is_part_time:
                result = calculate_part_time_amount(employee)
            else:
                result = calculate_full_time_amount(employee)
    return result
```

Command:
```bash
molting replace-nested-conditional-with-guard-clauses payroll.py::get_payment_amount#L2-L11
```

After:
```python
def get_payment_amount(employee):
    if employee.is_separated:
        return 0
    if employee.is_retired:
        return 0
    if employee.is_part_time:
        return calculate_part_time_amount(employee)
    return calculate_full_time_amount(employee)
```

---

## Replace Conditional with Polymorphism

**Description**: Move each leg of the conditional to an overriding method in a subclass.

**When to use**:
- Have conditional that chooses behavior based on object type
- Want to add new types without modifying existing code
- Conditional appears in multiple places

**Syntax**:
```bash
molting replace-conditional-with-polymorphism <target>#L<start>-L<end>
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
        else:
            raise ValueError("Invalid employee type")
```

Command:
```bash
molting replace-conditional-with-polymorphism employee.py::Employee::pay_amount#L10-L17
```

After:
```python
class Employee:
    def pay_amount(self):
        raise NotImplementedError

class Engineer(Employee):
    def pay_amount(self):
        return self.monthly_salary

class Salesman(Employee):
    def pay_amount(self):
        return self.monthly_salary + self.commission

class Manager(Employee):
    def pay_amount(self):
        return self.monthly_salary + self.bonus
```

---

## Introduce Null Object

**Description**: Replace null checks with a null object.

**When to use**:
- Checking for null in many places
- Null checks have the same behavior
- Want to eliminate conditional logic

**Syntax**:
```bash
molting introduce-null-object <target_class>
```

**Example**:

Before:
```python
class Site:
    def __init__(self, customer):
        self.customer = customer

class Customer:
    def __init__(self, name):
        self.name = name

# Client code
customer = site.customer
plan = customer.plan if customer is not None else "Basic"
name = customer.name if customer is not None else "Unknown"
```

Command:
```bash
molting introduce-null-object customer.py::Customer
```

After:
```python
class Site:
    def __init__(self, customer):
        self.customer = customer if customer is not None else NullCustomer()

class Customer:
    def __init__(self, name):
        self.name = name
        self.plan = "Premium"

    def is_null(self):
        return False

class NullCustomer(Customer):
    def __init__(self):
        self.name = "Unknown"
        self.plan = "Basic"

    def is_null(self):
        return True

# Client code
customer = site.customer
plan = customer.plan
name = customer.name
```

---

## Introduce Assertion

**Description**: Make the assumption explicit with an assertion.

**When to use**:
- Section of code assumes something about program state
- Want to make assumptions explicit
- Debugging would benefit from explicit checks

**Syntax**:
```bash
molting introduce-assertion <target>#L<line> --condition <assertion_condition>
```

**Example**:

Before:
```python
def get_expense_limit(project):
    # Should have either expense limit or primary project
    return project.expense_limit if project.expense_limit else project.primary_project.member_expense_limit
```

Command:
```bash
molting introduce-assertion expense.py::get_expense_limit#L3 --condition "project.expense_limit is not None or project.primary_project is not None"
```

After:
```python
def get_expense_limit(project):
    assert (project.expense_limit is not None or
            project.primary_project is not None), \
           "Project must have expense limit or primary project"
    return project.expense_limit if project.expense_limit else project.primary_project.member_expense_limit
```
