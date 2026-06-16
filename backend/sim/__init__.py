"""Parametric aerospace simulation core.

Sub-modules:
    atmosphere   -- ISA 1976 standard atmosphere
    propellant   -- solid propellant thermochemistry
    grain        -- parametric solid-propellant grain geometry + regression
    motor        -- solid rocket motor internal ballistics
    aerodynamics -- parametric drag model
    dynamics     -- 3-DOF point-mass flight integrator (RK4)
    guidance     -- proportional navigation guidance law
    engagement   -- interceptor-vs-target engagement simulation
    models       -- shared Pydantic parameter / result schemas
"""
