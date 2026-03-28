# Example Tutorial

## Big Idea

This Python lesson builds the program step by step across 4 teaching steps, covering 2 functions, 1 class, and a final execution flow. Along the way, students will encounter control flow, recursion, and state management.

## At a Glance

- Language: Python
- Suggested level: Advanced
- Estimated pacing: 20-30 minutes
- Lesson steps: 4
- Components covered: 2 functions, 1 class, and a final execution flow
- Core concepts: control flow, recursion, and state management



## Warm-Up

Ask students what has to be true for a recursive call to stop, then have them predict where that stopping case appears.


## Key Vocabulary

- `parameter`: a named input a function receives.
- `return value`: the result a function gives back to its caller.
- `class`: a reusable unit that groups related data and behavior.
- `method`: a behavior that belongs to a specific class.
- `state`: information an object keeps between actions.
- `recursion`: solving a problem by calling the same function on a smaller case.
- `control flow`: the decisions that determine which lines run next.



## What You'll Learn

- Trace how each function uses inputs, decisions, and return values.
- Describe how each class groups responsibilities and manages state.
- Connect the supporting definitions to the final execution flow.


## Teaching Tips

- Ask students to predict what the code will do before you reveal the explanation or run it.
- Have learners annotate where data enters, changes, and leaves the program.
- Pause after each step and connect it back to the overall goal.
- For recursion, trace one concrete call stack on paper and mark the stopping case before running the code.
- Separate what the class knows (state) from what it does (methods) so object-oriented structure feels less abstract.
- Use the final execution step as a recap: students should be able to explain every call it makes.


## Steps


### Step 1: Define `factorial`


> This function has no dependencies on other parts of the program, so it is a natural starting point.


Calculate factorial recursively.

**Focus**

`factorial` calls itself, so the key question is: where does the recursion stop?

**Look For**

- Inputs: `n`.
- Recursive — trace both the base case and the self-call.
- Returns a value — ask what and when.
- Contains a decision point — good for branch tracing.


**Ask Your Students**

- What single job does `factorial` do for the rest of the program?
- Which input changes the behavior of `factorial` the most: `n`?


```python
def factorial(n):
    """Calculate factorial recursively."""
    if n == 0:
        return 1
    else:
        return n * factorial(n - 1)
```

**Predict**

Trace `factorial(n=3)` by hand. How many times does it call itself before returning?

**Modify**

Change the base case in `factorial`. What happens to the recursion?

**Try It**

Change one argument to `factorial` and predict the new result before running the code.


### Step 2: Define `fibonacci`


> This function has no dependencies on other parts of the program, so it is a natural starting point.


Calculate nth Fibonacci number.

**Focus**

`fibonacci` calls itself, so the key question is: where does the recursion stop?

**Look For**

- Inputs: `n`.
- Recursive — trace both the base case and the self-call.
- Returns a value — ask what and when.
- Contains a decision point — good for branch tracing.


**Ask Your Students**

- What single job does `fibonacci` do for the rest of the program?
- Which input changes the behavior of `fibonacci` the most: `n`?


```python
def fibonacci(n):
    """Calculate nth Fibonacci number."""
    if n <= 1:
        return n
    else:
        return fibonacci(n - 1) + fibonacci(n - 2)
```

**Predict**

Trace `fibonacci(n=3)` by hand. How many times does it call itself before returning?

**Modify**

Change the base case in `fibonacci`. What happens to the recursion?

**Try It**

Change one argument to `fibonacci` and predict the new result before running the code.


### Step 3: Define the `Calculator` class


> This class is self-contained, making it a clean building block to introduce next.


A simple calculator class.

**Focus**

`Calculator` bundles related data and behavior into one reusable class.

**Look For**

- Methods: `__init__`, `add`, `multiply`.
- Carries state that persists across method calls.
- Ask what responsibilities belong inside this type and what should stay outside.


**Ask Your Students**

- What problem does `Calculator` solve better as a class than as loose code?
- Which method is the best starting point for understanding `Calculator`?


```python
class Calculator:
    """A simple calculator class."""

    def __init__(self):
        self.history = []

    def add(self, a, b):
        """Add two numbers."""
        result = a + b
        self.history.append(f"{a} + {b} = {result}")
        return result

    def multiply(self, a, b):
        """Multiply two numbers."""
        result = a * b
        self.history.append(f"{a} * {b} = {result}")
        return result
```

**Predict**

Create an instance of `Calculator` and call `__init__`. What do you get back?

**Modify**

Add one new method to `Calculator` that would make it more useful. Justify why that behavior belongs here.

**Try It**

Ask students to add one new method to `Calculator` and explain what behavior it should own.


### Step 4: Main Execution


> With all the definitions ready, we can now run the program.


The program runs by calling `factorial`, `fibonacci`, and `Calculator`, connecting the earlier definitions into a real result.

**Focus**

This is the orchestration step where the earlier building blocks run together as a complete program.

**Look For**

- This is where the earlier pieces come together into a full program run.
- Calls to trace: `factorial`, `fibonacci`, `Calculator`.
- Students should be able to explain this section using the previous steps.


**Ask Your Students**

- What happens first, second, and third when this section runs?
- Which earlier definition explains the behavior of `factorial`?


```python
if __name__ == "__main__":
    print(factorial(5))
    print(fibonacci(10))
    calc = Calculator()
    print(calc.add(3, 4))
    print(calc.multiply(5, 6))
    print(calc.history)
```

**Predict**

Before running, predict the output of the `factorial` call in this section.

**Modify**

Change one input value and predict the new output before running it.

**Try It**

Before running this section, ask students to predict the order of calls, outputs, or state changes.



## The Complete Program

```python
def factorial(n):
    """Calculate factorial recursively."""
    if n == 0:
        return 1
    else:
        return n * factorial(n - 1)


def fibonacci(n):
    """Calculate nth Fibonacci number."""
    if n <= 1:
        return n
    else:
        return fibonacci(n - 1) + fibonacci(n - 2)


class Calculator:
    """A simple calculator class."""

    def __init__(self):
        self.history = []

    def add(self, a, b):
        """Add two numbers."""
        result = a + b
        self.history.append(f"{a} + {b} = {result}")
        return result

    def multiply(self, a, b):
        """Multiply two numbers."""
        result = a * b
        self.history.append(f"{a} * {b} = {result}")
        return result


if __name__ == "__main__":
    print(factorial(5))
    print(fibonacci(10))

    calc = Calculator()
    print(calc.add(3, 4))
    print(calc.multiply(5, 6))
    print(calc.history)
```


## Checks for Understanding

- What essential job would disappear if `factorial` were removed?
- Where does data enter the program, and where does it leave?
- Which step would you revisit first if the final output were wrong?
- Which earlier definition does the final execution step rely on first?


## Extension Challenge

Rewrite the recursive logic iteratively, then compare which version is easier to explain and why.

## Recap

- Define `factorial`: trace the inputs, decisions, and outputs inside `factorial`.
- Define `fibonacci`: trace the inputs, decisions, and outputs inside `fibonacci`.
- Define the `Calculator` class: explain what responsibility `Calculator` owns.
- Main Execution: connect the earlier building blocks into one full execution.

