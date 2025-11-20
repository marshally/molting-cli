# Dealing with Generalization

Refactorings for managing inheritance hierarchies and relationships between classes.

## Pull Up Field

**Description**: Move a field from subclasses to the superclass.

**When to use**:
- Two subclasses have the same field
- Field is used in similar ways
- Want to eliminate duplication

**Syntax**:
```bash
molting pull-up-field <source>::<field_name> --to <superclass>
```

**Example**:

Before:
```python
class Salesman(Employee):
    def __init__(self, name):
        self.name = name

class Engineer(Employee):
    def __init__(self, name):
        self.name = name

class Employee:
    pass
```

Command:
```bash
molting pull-up-field salesman.py::Salesman::name --to Employee
```

After:
```python
class Salesman(Employee):
    def __init__(self, name):
        super().__init__(name)

class Engineer(Employee):
    def __init__(self, name):
        super().__init__(name)

class Employee:
    def __init__(self, name):
        self.name = name
```

---

## Pull Up Method

**Description**: Move identical methods from subclasses to the superclass.

**When to use**:
- Methods in subclasses have identical results
- Want to eliminate duplication
- Subclasses developed in parallel with duplicate methods

**Syntax**:
```bash
molting pull-up-method <source> --to <superclass>
```

**Example**:

Before:
```python
class Salesman(Employee):
    def get_annual_cost(self):
        return self.monthly_cost * 12

class Engineer(Employee):
    def get_annual_cost(self):
        return self.monthly_cost * 12

class Employee:
    pass
```

Command:
```bash
molting pull-up-method salesman.py::Salesman::get_annual_cost --to Employee
```

After:
```python
class Salesman(Employee):
    pass

class Engineer(Employee):
    pass

class Employee:
    def get_annual_cost(self):
        return self.monthly_cost * 12
```

---

## Pull Up Constructor Body

**Description**: Create a superclass constructor and call it from subclass constructors.

**When to use**:
- Constructors in subclasses have mostly identical bodies
- Want to eliminate duplication in initialization
- Subclasses have common setup logic

**Syntax**:
```bash
molting pull-up-constructor-body <source> --to <superclass>
```

**Example**:

Before:
```python
class Manager(Employee):
    def __init__(self, name, id, grade):
        self.name = name
        self.id = id
        self.grade = grade

class Engineer(Employee):
    def __init__(self, name, id):
        self.name = name
        self.id = id

class Employee:
    pass
```

Command:
```bash
molting pull-up-constructor-body manager.py::Manager::__init__ --to Employee
```

After:
```python
class Manager(Employee):
    def __init__(self, name, id, grade):
        super().__init__(name, id)
        self.grade = grade

class Engineer(Employee):
    def __init__(self, name, id):
        super().__init__(name, id)

class Employee:
    def __init__(self, name, id):
        self.name = name
        self.id = id
```

---

## Push Down Method

**Description**: Move a method from superclass to those subclasses that need it.

**When to use**:
- Behavior on superclass is relevant only for some subclasses
- Want to make class hierarchy clearer
- Method is used by only one or two subclasses

**Syntax**:
```bash
molting push-down-method <source> --to <subclass1,subclass2>
```

**Example**:

Before:
```python
class Employee:
    def get_quota(self):
        return 100

class Engineer(Employee):
    pass

class Salesman(Employee):
    pass
```

Command:
```bash
molting push-down-method employee.py::Employee::get_quota --to Salesman
```

After:
```python
class Employee:
    pass

class Engineer(Employee):
    pass

class Salesman(Employee):
    def get_quota(self):
        return 100
```

---

## Push Down Field

**Description**: Move a field from superclass to those subclasses that need it.

**When to use**:
- Field is used by only some subclasses
- Want to make class hierarchy clearer
- Field is relevant only for some subclasses

**Syntax**:
```bash
molting push-down-field <source>::<field_name> --to <subclass1,subclass2>
```

**Example**:

Before:
```python
class Employee:
    def __init__(self):
        self.quota = 0

class Engineer(Employee):
    pass

class Salesman(Employee):
    pass
```

Command:
```bash
molting push-down-field employee.py::Employee::quota --to Salesman
```

After:
```python
class Employee:
    pass

class Engineer(Employee):
    pass

class Salesman(Employee):
    def __init__(self):
        super().__init__()
        self.quota = 0
```

---

## Extract Subclass

**Description**: Create a subclass for a subset of features.

**When to use**:
- Class has features used only in some instances
- Class has conditional code based on type
- Want to clarify responsibilities

**Syntax**:
```bash
molting extract-subclass <source> --features <feature1,feature2> --name <SubclassName>
```

**Example**:

Before:
```python
class JobItem:
    def __init__(self, quantity, employee, is_labor):
        self.quantity = quantity
        self.employee = employee
        self.is_labor = is_labor

    def get_unit_price(self):
        if self.is_labor:
            return self.employee.rate
        return self.unit_price

    def get_total_price(self):
        return self.get_unit_price() * self.quantity
```

Command:
```bash
molting extract-subclass job.py::JobItem --features is_labor,employee --name LaborItem
```

After:
```python
class JobItem:
    def __init__(self, quantity, unit_price):
        self.quantity = quantity
        self.unit_price = unit_price

    def get_unit_price(self):
        return self.unit_price

    def get_total_price(self):
        return self.get_unit_price() * self.quantity

class LaborItem(JobItem):
    def __init__(self, quantity, employee):
        super().__init__(quantity, 0)
        self.employee = employee

    def get_unit_price(self):
        return self.employee.rate
```

---

## Extract Superclass

**Description**: Create a superclass and move common features to it.

**When to use**:
- Two classes have similar features
- Want to eliminate duplicate code
- Classes share common behavior

**Syntax**:
```bash
molting extract-superclass <class1> <class2> --name <SuperclassName>
```

**Example**:

Before:
```python
class Employee:
    def __init__(self, name, id, annual_cost):
        self.name = name
        self.id = id
        self.annual_cost = annual_cost

    def get_name(self):
        return self.name

    def get_id(self):
        return self.id

class Department:
    def __init__(self, name, staff):
        self.name = name
        self.staff = staff

    def get_name(self):
        return self.name

    def get_total_annual_cost(self):
        return sum(s.annual_cost for s in self.staff)
```

Command:
```bash
molting extract-superclass employee.py::Employee department.py::Department --name Party
```

After:
```python
class Party:
    def __init__(self, name):
        self.name = name

    def get_name(self):
        return self.name

class Employee(Party):
    def __init__(self, name, id, annual_cost):
        super().__init__(name)
        self.id = id
        self.annual_cost = annual_cost

    def get_id(self):
        return self.id

class Department(Party):
    def __init__(self, name, staff):
        super().__init__(name)
        self.staff = staff

    def get_total_annual_cost(self):
        return sum(s.annual_cost for s in self.staff)
```

---

## Extract Interface

**Description**: Create an interface for a common subset of methods.

**When to use**:
- Several clients use the same subset of a class's interface
- Two classes have part of their interfaces in common
- Want to make dependencies explicit (in typed Python with protocols)

**Syntax**:
```bash
molting extract-interface <source> --methods <method1,method2> --name <InterfaceName>
```

**Example**:

Before:
```python
class Employee:
    def get_rate(self):
        return self.rate

    def has_special_skill(self):
        return self.special_skill is not None

    def get_name(self):
        return self.name
```

Command:
```bash
molting extract-interface employee.py::Employee --methods get_rate,has_special_skill --name Billable
```

After:
```python
from typing import Protocol

class Billable(Protocol):
    def get_rate(self) -> float:
        ...

    def has_special_skill(self) -> bool:
        ...

class Employee:
    def get_rate(self):
        return self.rate

    def has_special_skill(self):
        return self.special_skill is not None

    def get_name(self):
        return self.name
```

---

## Collapse Hierarchy

**Description**: Merge a subclass into its superclass.

**When to use**:
- Subclass and superclass are not very different
- No longer need separate classes
- Hierarchy has become too complex

**Syntax**:
```bash
molting collapse-hierarchy <subclass> --into <superclass>
```

**Example**:

Before:
```python
class Employee:
    def __init__(self, name):
        self.name = name

    def get_name(self):
        return self.name

class Salesman(Employee):
    pass
```

Command:
```bash
molting collapse-hierarchy salesman.py::Salesman --into Employee
```

After:
```python
class Employee:
    def __init__(self, name):
        self.name = name

    def get_name(self):
        return self.name
```

---

## Form Template Method

**Description**: Put the invariant parts of the algorithm in the superclass and varying parts in subclasses.

**When to use**:
- Subclasses have methods with similar steps in same order
- Steps do similar but slightly different things
- Want to eliminate duplication while preserving variation

**Syntax**:
```bash
molting form-template-method <method1> <method2> --name <template_method_name>
```

**Example**:

Before:
```python
class Site:
    pass

class ResidentialSite(Site):
    def get_bill_amount(self):
        base = self.units * self.rate
        tax = base * Site.TAX_RATE
        return base + tax

class LifelineSite(Site):
    def get_bill_amount(self):
        base = self.units * self.rate * 0.5
        tax = base * Site.TAX_RATE * 0.2
        return base + tax
```

Command:
```bash
molting form-template-method residential.py::ResidentialSite::get_bill_amount lifeline.py::LifelineSite::get_bill_amount --name get_bill_amount
```

After:
```python
class Site:
    def get_bill_amount(self):
        base = self.get_base_amount()
        tax = self.get_tax_amount(base)
        return base + tax

    def get_base_amount(self):
        raise NotImplementedError

    def get_tax_amount(self, base):
        raise NotImplementedError

class ResidentialSite(Site):
    def get_base_amount(self):
        return self.units * self.rate

    def get_tax_amount(self, base):
        return base * Site.TAX_RATE

class LifelineSite(Site):
    def get_base_amount(self):
        return self.units * self.rate * 0.5

    def get_tax_amount(self, base):
        return base * Site.TAX_RATE * 0.2
```

---

## Replace Inheritance with Delegation

**Description**: Create a field for the superclass, adjust methods to delegate, and remove the subclassing.

**When to use**:
- Using only part of superclass interface
- Don't want to inherit superclass data
- Violating Liskov Substitution Principle

**Syntax**:
```bash
molting replace-inheritance-with-delegation <subclass>
```

**Example**:

Before:
```python
class Stack(list):
    def push(self, element):
        self.append(element)
```

Command:
```bash
molting replace-inheritance-with-delegation stack.py::Stack
```

After:
```python
class Stack:
    def __init__(self):
        self._items = []

    def push(self, element):
        self._items.append(element)

    def pop(self):
        return self._items.pop()

    def size(self):
        return len(self._items)
```

---

## Replace Delegation with Inheritance

**Description**: Make the delegating class a subclass of the delegate.

**When to use**:
- Using all methods of the delegate
- Lots of simple delegating methods
- Delegate interface is stable

**Syntax**:
```bash
molting replace-delegation-with-inheritance <delegating_class> --delegate <delegate_field>
```

**Example**:

Before:
```python
class Employee:
    def __init__(self, name):
        self._person = Person(name)

    def get_name(self):
        return self._person.name

    def set_name(self, name):
        self._person.name = name

    def get_last_name(self):
        return self._person.last_name

class Person:
    def __init__(self, name):
        self.name = name
        self.last_name = name.split()[-1]
```

Command:
```bash
molting replace-delegation-with-inheritance employee.py::Employee --delegate _person
```

After:
```python
class Employee(Person):
    def __init__(self, name):
        super().__init__(name)

class Person:
    def __init__(self, name):
        self.name = name
        self.last_name = name.split()[-1]
```
