# Composing Methods

Refactorings for improving the internal structure of methods by extracting, inlining, and reorganizing code.

## Extract Method

**Description**: Turn a code fragment into a method whose name explains the purpose of the method.

**When to use**:
- A method is too long
- Code needs a comment to explain what it does
- You want to reuse a piece of logic

**Syntax**:
```bash
molting extract-method <target>#L<start>-L<end> <new_method_name>
```

**Example**:

Before:
```python
# orders.py
class Order:
    def print_owing(self):
        outstanding = 0

        # print banner
        print("**************************")
        print("***** Customer Owes ******")
        print("**************************")

        # calculate outstanding
        for order in self.orders:
            outstanding += order.amount

        # print details
        print(f"name: {self.name}")
        print(f"amount: {outstanding}")
```

Command:
```bash
molting extract-method orders.py::Order::print_owing#L6-L8 print_banner
molting extract-method orders.py::Order::print_owing#L10-L12 calculate_outstanding
molting extract-method orders.py::Order::print_owing#L14-L16 print_details
```

After:
```python
class Order:
    def print_owing(self):
        self.print_banner()
        outstanding = self.calculate_outstanding()
        self.print_details(outstanding)

    def print_banner(self):
        print("**************************")
        print("***** Customer Owes ******")
        print("**************************")

    def calculate_outstanding(self):
        outstanding = 0
        for order in self.orders:
            outstanding += order.amount
        return outstanding

    def print_details(self, outstanding):
        print(f"name: {self.name}")
        print(f"amount: {outstanding}")
```

---

## Extract Function

**Description**: Extract code into a module-level function when it doesn't need instance state.

**When to use**:
- Code doesn't use instance variables
- Logic is generally useful outside the class
- You want to make a utility function

**Syntax**:
```bash
molting extract-function <target>#L<start>-L<end> <new_function_name>
```

**Example**:

Before:
```python
# utils.py
class DataProcessor:
    def process(self, data):
        # format the data
        formatted = data.strip().lower().replace(" ", "_")
        return formatted
```

Command:
```bash
molting extract-function utils.py::DataProcessor::process#L4 normalize_string
```

After:
```python
def normalize_string(data):
    return data.strip().lower().replace(" ", "_")

class DataProcessor:
    def process(self, data):
        return normalize_string(data)
```

---

## Inline Method

**Description**: Replace calls to a method with the method's body when the method body is as clear as its name.

**When to use**:
- Method body is as clear as the method name
- Method is only called from one place
- Indirection is needless

**Syntax**:
```bash
molting inline-method <target>
```

**Example**:

Before:
```python
class Person:
    def get_rating(self):
        return 2 if self.more_than_five_late_deliveries() else 1

    def more_than_five_late_deliveries(self):
        return self.late_deliveries > 5
```

Command:
```bash
molting inline-method person.py::Person::more_than_five_late_deliveries
```

After:
```python
class Person:
    def get_rating(self):
        return 2 if self.late_deliveries > 5 else 1
```

---

## Inline Temp

**Description**: Replace a temporary variable with the expression that creates it.

**When to use**:
- Temp is assigned once from a simple expression
- Temp is getting in the way of other refactorings like Extract Method

**Syntax**:
```bash
molting inline-temp <target>::<variable_name>
```

**Example**:

Before:
```python
def calculate_total(order):
    base_price = order.quantity * order.item_price
    return base_price > 1000
```

Command:
```bash
molting inline-temp calculate.py::calculate_total::base_price
```

After:
```python
def calculate_total(order):
    return order.quantity * order.item_price > 1000
```

---

## Replace Temp with Query

**Description**: Extract the expression into a method and replace all references to the temp with the method call.

**When to use**:
- Using a temp to hold the result of an expression
- Want to extract other code that needs this calculation
- The temp is assigned to only once

**Syntax**:
```bash
molting replace-temp-with-query <target>::<variable_name>
```

**Example**:

Before:
```python
class Order:
    def get_price(self):
        base_price = self.quantity * self.item_price
        discount_factor = 0.98 if base_price > 1000 else 0.95
        return base_price * discount_factor
```

Command:
```bash
molting replace-temp-with-query order.py::Order::get_price::base_price
```

After:
```python
class Order:
    def get_price(self):
        discount_factor = 0.98 if self.base_price() > 1000 else 0.95
        return self.base_price() * discount_factor

    def base_price(self):
        return self.quantity * self.item_price
```

---

## Introduce Explaining Variable

**Description**: Put the result of a complex expression into a temporary variable with a name that explains the purpose.

**When to use**:
- Complex expression is hard to read
- Expression is used multiple times
- Conditional logic needs clarity

**Syntax**:
```bash
molting introduce-explaining-variable <target>#L<line> <variable_name>
```

**Example**:

Before:
```python
def calculate_total(order):
    return (order.quantity * order.item_price -
            max(0, order.quantity - 500) * order.item_price * 0.05 +
            min(order.quantity * order.item_price * 0.1, 100.0))
```

Command:
```bash
molting introduce-explaining-variable calculate.py::calculate_total#L2 base_price
molting introduce-explaining-variable calculate.py::calculate_total#L3 quantity_discount
molting introduce-explaining-variable calculate.py::calculate_total#L4 shipping
```

After:
```python
def calculate_total(order):
    base_price = order.quantity * order.item_price
    quantity_discount = max(0, order.quantity - 500) * order.item_price * 0.05
    shipping = min(base_price * 0.1, 100.0)
    return base_price - quantity_discount + shipping
```

---

## Split Temporary Variable

**Description**: Make a separate temporary variable for each assignment when a temp is assigned to more than once.

**When to use**:
- A temporary variable is assigned to more than once
- The temp is not a loop variable or collecting temp
- Each assignment has a different purpose

**Syntax**:
```bash
molting split-temporary-variable <target>::<variable_name>
```

**Example**:

Before:
```python
def calculate_distance(scenario):
    temp = 2 * (scenario.primary_force / scenario.mass)
    primary_time = scenario.delay

    temp = scenario.secondary_force / scenario.mass
    secondary_time = scenario.delay + temp
```

Command:
```bash
molting split-temporary-variable physics.py::calculate_distance::temp
```

After:
```python
def calculate_distance(scenario):
    primary_acc = 2 * (scenario.primary_force / scenario.mass)
    primary_time = scenario.delay

    secondary_acc = scenario.secondary_force / scenario.mass
    secondary_time = scenario.delay + secondary_acc
```

---

## Remove Assignments to Parameters

**Description**: Use a temporary variable instead of assigning to a parameter.

**When to use**:
- Code assigns to a parameter
- Parameter reassignment is confusing
- Following pass-by-value semantics

**Syntax**:
```bash
molting remove-assignments-to-parameters <target>
```

**Example**:

Before:
```python
def discount(input_val, quantity, year_to_date):
    if input_val > 50:
        input_val -= 2
    if quantity > 100:
        input_val -= 1
    if year_to_date > 10000:
        input_val -= 4
    return input_val
```

Command:
```bash
molting remove-assignments-to-parameters discount.py::discount
```

After:
```python
def discount(input_val, quantity, year_to_date):
    result = input_val
    if result > 50:
        result -= 2
    if quantity > 100:
        result -= 1
    if year_to_date > 10000:
        result -= 4
    return result
```

---

## Replace Method with Method Object

**Description**: Turn the method into its own object so that local variables become fields on that object.

**When to use**:
- Long method with many local variables and parameters
- Can't easily use Extract Method due to variable dependencies
- Method has complex logic that needs to be broken down

**Syntax**:
```bash
molting replace-method-with-method-object <target>
```

**Example**:

Before:
```python
class Account:
    def gamma(self, input_val, quantity, year_to_date):
        important_value1 = (input_val * quantity) + self.delta()
        important_value2 = (input_val * year_to_date) + 100
        important_thing = self._important_thing(important_value1, important_value2)
        return important_thing - 2 * important_value1

    def _important_thing(self, val1, val2):
        return val1 * val2
```

Command:
```bash
molting replace-method-with-method-object account.py::Account::gamma
```

After:
```python
class Account:
    def gamma(self, input_val, quantity, year_to_date):
        return Gamma(self, input_val, quantity, year_to_date).compute()

class Gamma:
    def __init__(self, account, input_val, quantity, year_to_date):
        self.account = account
        self.input_val = input_val
        self.quantity = quantity
        self.year_to_date = year_to_date

    def compute(self):
        important_value1 = (self.input_val * self.quantity) + self.account.delta()
        important_value2 = (self.input_val * self.year_to_date) + 100
        important_thing = self._important_thing(important_value1, important_value2)
        return important_thing - 2 * important_value1

    def _important_thing(self, val1, val2):
        return val1 * val2
```

---

## Substitute Algorithm

**Description**: Replace an algorithm with one that is clearer or more efficient.

**When to use**:
- Found a clearer way to do something
- Want to replace complex algorithm with simpler one
- Need to change implementation approach

**Syntax**:
```bash
molting substitute-algorithm <target>
```

**Example**:

Before:
```python
def found_person(people):
    for person in people:
        if person == "Don":
            return "Don"
        if person == "John":
            return "John"
        if person == "Kent":
            return "Kent"
    return ""
```

Command:
```bash
molting substitute-algorithm search.py::found_person
```

After:
```python
def found_person(people):
    candidates = ["Don", "John", "Kent"]
    for person in people:
        if person in candidates:
            return person
    return ""
```
