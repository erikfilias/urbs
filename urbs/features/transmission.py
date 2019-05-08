import math
import pyomo.core as pyomo


def remove_duplicate_transmission(transmission_keys):
    tra_tuple_list = list(transmission_keys)
    i = 0
    while i < len(tra_tuple_list):
        for k in range(len(tra_tuple_list)):
            if (tra_tuple_list[i][1] == tra_tuple_list[k][2] and
                    tra_tuple_list[i][2] == tra_tuple_list[k][1]):
                del tra_tuple_list[i]
                i -= 1
                break
        i += 1
    return set(tra_tuple_list)


def add_transmission(m):

    # tranmission (e.g. hvac, hvdc, pipeline...)
    indexlist = set()
    for key in m.transmission_dict["eff"]:
        indexlist.add(tuple(key)[3])
    m.tra = pyomo.Set(
        initialize=indexlist,
        doc='Set of transmission technologies')

    # transmission tuples
    m.tra_tuples = pyomo.Set(
        within=m.stf * m.sit * m.sit * m.tra * m.com,
        initialize=tuple(m.transmission_dict["eff"].keys()),
        doc='Combinations of possible transmissions, e.g. '
            '(2020,South,Mid,hvac,Elec)')

    if m.mode['int']:
        m.operational_tra_tuples = pyomo.Set(
            within=m.sit * m.sit * m.tra * m.com * m.stf * m.stf,
            initialize=[(sit, sit_, tra, com, stf, stf_later)
                        for (sit, sit_, tra, com, stf, stf_later)
                        in op_tra_tuples(m.tra_tuples, m)],
            doc='Transmissions that are still operational through stf_later'
                '(and the relevant years following), if built in stf'
                'in stf.')
        m.inst_tra_tuples = pyomo.Set(
            within=m.sit * m.sit * m.tra * m.com * m.stf,
            initialize=[(sit, sit_, tra, com, stf)
                        for (sit, sit_, tra, com, stf)
                        in inst_tra_tuples(m)],
            doc='Installed transmissions that are still operational'
                'through stf')

    # Variables
    m.cap_tra_new = pyomo.Var(
        m.tra_tuples,
        within=pyomo.NonNegativeReals,
        doc='New transmission capacity (MW)')

    # transmission capacity as expression object
    m.cap_tra = pyomo.Expression(
        m.tra_tuples,
        rule=def_transmission_capacity_rule,
        doc='total transmission capacity')

    m.e_tra_in = pyomo.Var(
        m.tm, m.tra_tuples,
        within=pyomo.NonNegativeReals,
        doc='Power flow into transmission line (MW) per timestep')
    m.e_tra_out = pyomo.Var(
        m.tm, m.tra_tuples,
        within=pyomo.NonNegativeReals,
        doc='Power flow out of transmission line (MW) per timestep')

    # transmission
    m.def_transmission_output = pyomo.Constraint(
        m.tm, m.tra_tuples,
        rule=def_transmission_output_rule,
        doc='transmission output = transmission input * efficiency')
    m.res_transmission_input_by_capacity = pyomo.Constraint(
        m.tm, m.tra_tuples,
        rule=res_transmission_input_by_capacity_rule,
        doc='transmission input <= total transmission capacity')
    m.res_transmission_capacity = pyomo.Constraint(
        m.tra_tuples,
        rule=res_transmission_capacity_rule,
        doc='transmission.cap-lo <= total transmission capacity <= '
            'transmission.cap-up')
    m.res_transmission_symmetry = pyomo.Constraint(
        m.tra_tuples,
        rule=res_transmission_symmetry_rule,
        doc='total transmission capacity must be symmetric in both directions')

    return m


def add_transmission_dc(m):

    tra_tuples = set()
    tra_tuples_dc = set()
    for key in m.transmission_dict['admittance']:
        tra_tuples.add(tuple(key))
        if m.transmission_dict['admittance'][key] > 0:
            tra_tuples_dc.add(tuple(key))
    tra_tuples_tp = tra_tuples - tra_tuples_dc
    tra_tuples_dc = remove_duplicate_transmission(tra_tuples_dc)
    tra_tuples = tra_tuples_dc | tra_tuples_tp

    # tranmission (e.g. hvac, hvdc, pipeline...)
    indexlist = set()
    for key in m.transmission_dict["eff"]:
        indexlist.add(tuple(key)[3])
    m.tra = pyomo.Set(
        initialize=indexlist,
        doc='Set of transmission technologies')

    # transmission tuples
    m.tra_tuples = pyomo.Set(
        within=m.stf * m.sit * m.sit * m.tra * m.com,
        initialize=tuple(tra_tuples),
        doc='Combinations of possible transmissions,'
            'without duplicate dc transmissions'
            ' e.g. (2020,South,Mid,hvac,Elec)')

    m.tra_tuples_dc = pyomo.Set(
        within=m.stf * m.sit * m.sit * m.tra * m.com,
        initialize=tuple(tra_tuples_dc),
        doc='Combinations of possible bidirectional dc'
            'transmissions, e.g. (2020,South,Mid,hvac,Elec)')

    m.tra_tuples_tp = pyomo.Set(
        within=m.stf * m.sit * m.sit * m.tra * m.com,
        initialize=tuple(tra_tuples_tp),
        doc='Combinations of possible transport transmissions,'
            'e.g. (2020,South,Mid,hvac,Elec)')

    if m.mode['int']:
        m.operational_tra_tuples = pyomo.Set(
            within=m.sit * m.sit * m.tra * m.com * m.stf * m.stf,
            initialize=[(sit, sit_, tra, com, stf, stf_later)
                        for (sit, sit_, tra, com, stf, stf_later)
                        in op_tra_tuples(m.tra_tuples, m)],
            doc='Transmissions that are still operational through stf_later'
                '(and the relevant years following), if built in stf'
                'in stf.')
        m.inst_tra_tuples = pyomo.Set(
            within=m.sit * m.sit * m.tra * m.com * m.stf,
            initialize=[(sit, sit_, tra, com, stf)
                        for (sit, sit_, tra, com, stf)
                        in inst_tra_tuples(m)],
            doc='Installed transmissions that are still operational'
                'through stf')

    # Variables
    m.cap_tra_new = pyomo.Var(
        m.tra_tuples,
        within=pyomo.NonNegativeReals,
        doc='New transmission capacity (MW)')

    # transmission capacity as expression object
    m.cap_tra = pyomo.Expression(
        m.tra_tuples,
        rule=def_transmission_capacity_rule,
        doc='total transmission capacity')

    m.e_tra_dc_in = pyomo.Var(
        m.tm, m.tra_tuples_dc,
        within=pyomo.Reals,
        doc='Power flow into transmission line (MW) per timestep')
    m.abs_e_tra_dc_in = pyomo.Var(
        m.tm, m.tra_tuples_dc,
        within=pyomo.NonNegativeReals,
        doc='Power flow into transmission line (MW) per timestep')
    m.e_tra_in = pyomo.Var(
        m.tm, m.tra_tuples_tp,
        within=pyomo.NonNegativeReals,
        doc='Power flow into transmission line (MW) per timestep')
    m.e_tra_dc_out = pyomo.Var(
        m.tm, m.tra_tuples_dc,
        within=pyomo.Reals,
        doc='Power flow out of transmission line (MW) per timestep')
    m.e_tra_out = pyomo.Var(
        m.tm, m.tra_tuples_tp,
        within=pyomo.NonNegativeReals,
        doc='Power flow out of transmission line (MW) per timestep')

    m.phase_angle = pyomo.Var(
        m.tm, m.stf, m.sit,
        within=pyomo.Reals,
        doc='Phase angle of a site')

    # transmission
    m.def_transmission_output = pyomo.Constraint(
        m.tm, m.tra_tuples_tp,
        rule=def_transmission_output_rule,
        doc='transmission output = transmission input * efficiency')
    m.def_transmission_dc_output = pyomo.Constraint(
        m.tm, m.tra_tuples_dc,
        rule=def_transmission_dc_output_rule,
        doc='transmission output = transmission input')
    m.def_dc_power_flow = pyomo.Constraint(
        m.tm, m.tra_tuples_dc,
        rule=def_dc_power_flow_rule,
        doc='transmission output = (angle(in)-angle(out)) * admittance')
    m.abs1_e_tra_dc_in = pyomo.Constraint(
        m.tm, m.tra_tuples_dc,
        rule=abs1_e_tra_dc_in_rule,
        doc='transmission dc input <= absolute transmission dc input')
    m.abs2_e_tra_dc_in = pyomo.Constraint(
        m.tm, m.tra_tuples_dc,
        rule=abs2_e_tra_dc_in_rule,
        doc='- transmission dc input <= absolute transmission dc input')

    m.res_transmission_input_by_capacity = pyomo.Constraint(
        m.tm, m.tra_tuples_tp,
        rule=res_transmission_input_by_capacity_rule,
        doc='transmission input <= total transmission capacity')
    m.res_transmission_dc_input_by_capacity = pyomo.Constraint(
        m.tm, m.tra_tuples_dc,
        rule=res_transmission_dc_input_by_capacity_rule,
        doc='-transmission input <= total transmission capacity')
    m.res_transmission_dc_input_by_neg_capacity = pyomo.Constraint(
        m.tm, m.tra_tuples_dc,
        rule=res_transmission_dc_input_by_neg_capacity_rule,
        doc='-transmission input <= total transmission capacity')
    m.res_transmission_capacity = pyomo.Constraint(
        m.tra_tuples,
        rule=res_transmission_capacity_rule,
        doc='transmission.cap-lo <= total transmission capacity <= '
            'transmission.cap-up')
    m.res_transmission_symmetry = pyomo.Constraint(
        m.tra_tuples_tp,
        rule=res_transmission_symmetry_rule,
        doc='total transmission capacity must be symmetric in both directions')

    return m


# constraints

# transmission capacity (for m.cap_tra expression)
def def_transmission_capacity_rule(m, stf, sin, sout, tra, com):
    if m.mode['int']:
        if (sin, sout, tra, com, stf) in m.inst_tra_tuples:
            if (min(m.stf), sin, sout, tra, com) in m.tra_const_cap_dict:
                cap_tra = m.transmission_dict['inst-cap'][
                    (stf, sin, sout, tra, com)]
            else:
                cap_tra = (
                    sum(m.cap_tra_new[stf_built, sin, sout, tra, com]
                        for stf_built in m.stf
                        if (sin, sout, tra, com, stf_built, stf) in
                        m.operational_tra_tuples) +
                    m.transmission_dict['inst-cap']
                    [(min(m.stf), sin, sout, tra, com)])
        else:
            cap_tra = (
                sum(m.cap_tra_new[stf_built, sin, sout, tra, com]
                    for stf_built in m.stf
                    if (sin, sout, tra, com, stf_built, stf) in
                    m.operational_tra_tuples))
    else:
        if (stf, sin, sout, tra, com) in m.tra_const_cap_dict:
            cap_tra = \
                m.transmission_dict['inst-cap'][(stf, sin, sout, tra, com)]
        else:
            cap_tra = (m.cap_tra_new[stf, sin, sout, tra, com] +
                       m.transmission_dict['inst-cap'][
                           (stf, sin, sout, tra, com)])

    return cap_tra

# transmission output == transmission input * efficiency


def def_transmission_output_rule(m, tm, stf, sin, sout, tra, com):
    return (m.e_tra_out[tm, stf, sin, sout, tra, com] ==
            m.e_tra_in[tm, stf, sin, sout, tra, com] *
            m.transmission_dict['eff'][(stf, sin, sout, tra, com)])


def def_transmission_dc_output_rule(m, tm, stf, sin, sout, tra, com):
    return m.e_tra_dc_out[tm, stf, sin, sout, tra, com] == m.e_tra_dc_in[tm, stf, sin, sout, tra, com]


# transmission input <= transmission capacity
def res_transmission_input_by_capacity_rule(m, tm, stf, sin, sout, tra, com):
    return (m.e_tra_in[tm, stf, sin, sout, tra, com] <=
            m.dt * m.cap_tra[stf, sin, sout, tra, com])


# transmission input <= transmission capacity
def res_transmission_dc_input_by_capacity_rule(m, tm, stf, sin, sout, tra, com):
    return (m.e_tra_dc_in[tm, stf, sin, sout, tra, com] <=
            (m.dt * m.cap_tra[stf, sin, sout, tra, com]))


def res_transmission_dc_input_by_neg_capacity_rule(m, tm, stf, sin, sout, tra, com):
    return (m.e_tra_dc_in[tm, stf, sin, sout, tra, com] >=
            (- m.dt * m.cap_tra[stf, sin, sout, tra, com]))


# lower bound <= transmission capacity <= upper bound
def res_transmission_capacity_rule(m, stf, sin, sout, tra, com):
    return (m.transmission_dict['cap-lo'][(stf, sin, sout, tra, com)],
            m.cap_tra[stf, sin, sout, tra, com],
            m.transmission_dict['cap-up'][(stf, sin, sout, tra, com)])


# transmission capacity from A to B == transmission capacity from B to A
def res_transmission_symmetry_rule(m, stf, sin, sout, tra, com):
    return m.cap_tra[stf, sin, sout, tra, com] == (m.cap_tra

                                                   [stf, sout, sin, tra, com])
def def_dc_power_flow_rule(m, tm, stf, sin, sout, tra, com):
    return (m.e_tra_dc_out[tm, stf, sin, sout, tra, com] ==
            (m.phase_angle[tm, stf, sin] - m.phase_angle[tm, stf, sout]) *
            m.transmission_dict['admittance'][(stf, sin, sout, tra, com)])


def abs1_e_tra_dc_in_rule(m, tm, stf, sin, sout, tra, com):
    return (m.e_tra_dc_in[tm, stf, sin, sout, tra, com] <=
            m.abs_e_tra_dc_in[tm, stf, sin, sout, tra, com])


def abs2_e_tra_dc_in_rule(m, tm, stf, sin, sout, tra, com):
    return (-m.e_tra_dc_in[tm, stf, sin, sout, tra, com] <=
            m.abs_e_tra_dc_in[tm, stf, sin, sout, tra, com])


# transmission balance
def transmission_balance(m, tm, stf, sit, com):
    """called in commodity balance
    For a given commodity co and timestep tm, calculate the balance of
    import and export """
    if m.mode['dpf']:
        return (sum(m.e_tra_in[(tm, stframe, site_in, site_out,
                                transmission, com)]
                    # exports increase balance
                    for stframe, site_in, site_out, transmission, commodity
                    in m.tra_tuples_tp
                    if (site_in == sit and stframe == stf and commodity ==
                    com)) +
                sum(m.e_tra_dc_in[(tm, stframe, site_in, site_out,
                                transmission, com)]
                    # exports increase balance
                    for stframe, site_in, site_out, transmission, commodity
                    in m.tra_tuples_dc
                    if (site_in == sit and stframe == stf and commodity ==
                        com)) -
                sum(m.e_tra_out[(tm, stframe, site_in, site_out,
                                 transmission, com)]
                    # imports decrease balance
                    for stframe, site_in, site_out, transmission, commodity
                    in m.tra_tuples_tp
                    if (site_out == sit and stframe == stf and
                    commodity == com)) -
                sum(m.e_tra_dc_out[(tm, stframe, site_in, site_out,
                                 transmission, com)]
                    # imports decrease balance
                    for stframe, site_in, site_out, transmission, commodity
                    in m.tra_tuples_dc
                    if (site_out == sit and stframe == stf and
                    commodity == com)))
    else:
        return (sum(m.e_tra_in[(tm, stframe, site_in, site_out,
                                transmission, com)]
                    # exports increase balance
                    for stframe, site_in, site_out, transmission, commodity
                    in m.tra_tuples
                    if (site_in == sit and stframe == stf and commodity ==
                    com)) -
                sum(m.e_tra_out[(tm, stframe, site_in, site_out,
                                 transmission, com)]
                    # imports decrease balance
                    for stframe, site_in, site_out, transmission, commodity
                    in m.tra_tuples
                    if site_out == sit and stframe == stf and
                    commodity == com))


# transmission cost function
def transmission_cost(m, cost_type):
    """returns transmission cost function for the different cost types"""
    if m.mode['dpf']:
        if cost_type == 'Invest':
            cost = sum(m.cap_tra_new[t] *
                       m.transmission_dict['inv-cost'][t] *
                       m.transmission_dict['invcost-factor'][t]
                       for t in m.tra_tuples_tp) + \
                   sum(m.cap_tra_new[t] * 2 *
                       m.transmission_dict['inv-cost'][t] *
                       m.transmission_dict['invcost-factor'][t]
                       for t in m.tra_tuples_dc)
            if m.mode['int']:
                cost -= sum(m.cap_tra_new[t] *
                            m.transmission_dict['inv-cost'][t] *
                            m.transmission_dict['overpay-factor'][t]
                            for t in m.tra_tuples_tp) + \
                        sum(m.cap_tra_new[t] * 2 *
                            m.transmission_dict['inv-cost'][t] *
                            m.transmission_dict['overpay-factor'][t]
                            for t in m.tra_tuples_dc)
            return cost
        elif cost_type == 'Fixed':
            return sum(m.cap_tra[t] * m.transmission_dict['fix-cost'][t] *
                       m.transmission_dict['cost_factor'][t]
                       for t in m.tra_tuples_tp) + \
                   sum(m.cap_tra[t] * 2 * m.transmission_dict['fix-cost'][t] *
                       m.transmission_dict['cost_factor'][t]
                       for t in m.tra_tuples_dc)
        elif cost_type == 'Variable':
            return sum(m.e_tra_in[(tm,) + t] * m.weight *
                       m.transmission_dict['var-cost'][t] *
                       m.transmission_dict['cost_factor'][t]
                       for tm in m.tm
                       for t in m.tra_tuples_tp) + \
                   sum(m.abs_e_tra_dc_in[(tm,) + t] * m.weight *
                       m.transmission_dict['var-cost'][t] *
                       m.transmission_dict['cost_factor'][t]
                       for tm in m.tm
                       for t in m.tra_tuples_dc)
    else:

        if cost_type == 'Invest':
            cost = sum(m.cap_tra_new[t] *
                       m.transmission_dict['inv-cost'][t] *
                       m.transmission_dict['invcost-factor'][t]
                       for t in m.tra_tuples)
            if m.mode['int']:
                cost -= sum(m.cap_tra_new[t] *
                            m.transmission_dict['inv-cost'][t] *
                            m.transmission_dict['overpay-factor'][t]
                            for t in m.tra_tuples)
            return cost
        elif cost_type == 'Fixed':
            return sum(m.cap_tra[t] * m.transmission_dict['fix-cost'][t] *
                       m.transmission_dict['cost_factor'][t]
                       for t in m.tra_tuples)
        elif cost_type == 'Variable':
            return sum(m.e_tra_in[(tm,) + t] * m.weight *
                       m.transmission_dict['var-cost'][t] *
                       m.transmission_dict['cost_factor'][t]
                       for tm in m.tm
                       for t in m.tra_tuples)


def op_tra_tuples(tra_tuple, m):
    """ s.a. op_pro_tuples
    """
    op_tra = []
    sorted_stf = sorted(list(m.stf))

    for (stf, sit1, sit2, tra, com) in tra_tuple:
        for stf_later in sorted_stf:
            index_helper = sorted_stf.index(stf_later)
            if stf_later == max(sorted_stf):
                if (stf_later +
                    m.global_prop_dict['value'][(max(sorted_stf), 'Weight')] -
                    1 <= stf + m.transmission_dict['depreciation'][
                        (stf, sit1, sit2, tra, com)]):
                    op_tra.append((sit1, sit2, tra, com, stf, stf_later))
            elif (sorted_stf[index_helper + 1] <=
                  stf + m.transmission_dict['depreciation'][
                      (stf, sit1, sit2, tra, com)] and stf <= stf_later):
                op_tra.append((sit1, sit2, tra, com, stf, stf_later))
            else:
                pass

    return op_tra


def inst_tra_tuples(m):
    """ s.a. inst_pro_tuples
    """
    inst_tra = []
    sorted_stf = sorted(list(m.stf))

    for (stf, sit1, sit2, tra, com) in m.inst_tra.index:
        for stf_later in sorted_stf:
            index_helper = sorted_stf.index(stf_later)
            if stf_later == max(m.stf):
                if (stf_later +
                    m.global_prop_dict['value'][(max(sorted_stf), 'Weight')] -
                    1 < min(m.stf) + m.transmission_dict['lifetime'][
                        (stf, sit1, sit2, tra, com)]):
                    inst_tra.append((sit1, sit2, tra, com, stf_later))
            elif (sorted_stf[index_helper + 1] <= min(m.stf) +
                  m.transmission_dict['lifetime'][
                      (stf, sit1, sit2, tra, com)]):
                inst_tra.append((sit1, sit2, tra, com, stf_later))

    return inst_tra
