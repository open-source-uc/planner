"""
Validation of a career plan.

A career plan is simply a list of semesters, every semester consisting of a list of
classes.
Some semesters are considered approved and are not validated, while other semesters are
considered planned and have to be validated.

Overall validation can be divided into two separate validation passes:
- Course validation: Make sure each individual planned course has their requirements
    met. Approved classes are not validated in this step. This is a logical validation,
    and is modelled as a logical expression for each class that must be satisfied.
- Curriculum validation: Make sure the set of approved and planned courses satisfy the
    selected curriculum. This validation is modelled using a flow network, where each
    course provides credits and the curriculum consumes credits.
"""
