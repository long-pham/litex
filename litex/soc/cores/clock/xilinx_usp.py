#
# This file is part of LiteX.
#
# Copyright (c) 2018-2020 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause

from litex.gen import *

from litex.soc.cores.clock.common import *
from litex.soc.cores.clock.xilinx_common import *
import numpy as np

# Xilinx / Ultrascale Plus -------------------------------------------------------------------------

# TODO:
# - use Ultrascale Plus primitives instead of 7-Series' ones. (Vivado recognize and convert them).

class USPPLL(XilinxClocking):
    nclkouts_max = 6

    def __init__(self, speedgrade=-1):
        self.logger = logging.getLogger("USPPLL")
        self.logger.info("Creating USPPLL, {}.".format(colorer("speedgrade {}".format(speedgrade))))
        XilinxClocking.__init__(self)
        self.divclk_divide_range = (1, 56+1)
        self.clkin_freq_range = {
            -1: (70e6,  800e6),
            -2: (70e6,  933e6),
            -3: (70e6, 1066e6),
        }[speedgrade]
        self.vco_freq_range = {
            -1: (750e6, 1500e6),
            -2: (750e6, 1500e6),
            -3: (750e6, 1500e6),
        }[speedgrade]

    def do_finalize(self):
        XilinxClocking.do_finalize(self)
        config = self.compute_config()
        pll_fb = Signal()
        self.params.update(
            # Global.
            p_STARTUP_WAIT = "FALSE",
            i_RST          = self.reset,
            i_PWRDWN       = self.power_down,
            o_LOCKED       = self.locked,

            # VCO.
            p_REF_JITTER1   = 0.01,
            p_CLKIN1_PERIOD = 1e9/self.clkin_freq,
            p_CLKFBOUT_MULT = config["clkfbout_mult"],
            p_DIVCLK_DIVIDE = config["divclk_divide"],
            i_CLKIN1        = self.clkin,
            i_CLKFBIN       = pll_fb,
            o_CLKFBOUT      = pll_fb,
        )
        for n, (clk, f, p, m) in sorted(self.clkouts.items()):
            self.params["p_CLKOUT{}_DIVIDE".format(n)] = config["clkout{}_divide".format(n)]
            self.params["p_CLKOUT{}_PHASE".format(n)]  = config["clkout{}_phase".format(n)]
            self.params["o_CLKOUT{}".format(n)]        = clk
        self.specials += Instance("PLLE2_ADV", **self.params)


class USPMMCM(XilinxClocking):
    nclkouts_max = 7

    def __init__(self, speedgrade=-1):
        self.logger = logging.getLogger("USPMMCM")
        self.logger.info("Creating USPMMCM, {}.".format(colorer("speedgrade {}".format(speedgrade))))
        XilinxClocking.__init__(self)
        self.divclk_divide_range = (1, 106+1)
        self.clkin_freq_range = {
            -1: (10e6,  800e6),
            -2: (10e6,  933e6),
            -3: (10e6, 1066e6),
        }[speedgrade]
        self.vco_freq_range = {
            -1: (800e6, 1600e6),
            -2: (800e6, 1600e6),
            -3: (800e6, 1600e6),
        }[speedgrade]

    def do_finalize(self):
        XilinxClocking.do_finalize(self)
        config = self.compute_config()
        mmcm_fb = Signal()
        self.params.update(
            # Global.
            p_BANDWIDTH = "OPTIMIZED",
            i_RST       = self.reset,
            i_PWRDWN    = self.power_down,
            o_LOCKED    = self.locked,

            # VCO.
            p_REF_JITTER1     = 0.01,
            p_CLKIN1_PERIOD   = 1e9/self.clkin_freq,
            p_CLKFBOUT_MULT_F = config["clkfbout_mult"],
            p_DIVCLK_DIVIDE   = config["divclk_divide"],
            i_CLKIN1          = self.clkin,
            i_CLKFBIN         = mmcm_fb,
            o_CLKFBOUT        = mmcm_fb,
        )
        for n, (clk, f, p, m) in sorted(self.clkouts.items()):
            if n == 0:
                self.params["p_CLKOUT{}_DIVIDE_F".format(n)] = config["clkout{}_divide".format(n)]
            else:
                self.params["p_CLKOUT{}_DIVIDE".format(n)] = config["clkout{}_divide".format(n)]
            self.params["p_CLKOUT{}_PHASE".format(n)] = config["clkout{}_phase".format(n)]
            self.params["o_CLKOUT{}".format(n)]       = clk
        self.specials += Instance("MMCME2_ADV", **self.params)

    def compute_config(self):
        config = {}
        # import pdb; pdb.set_trace()
        for divclk_divide in range(*self.divclk_divide_range):
            config["divclk_divide"] = divclk_divide
            for clkfbout_mult in reversed(np.arange(2, 128.1, 0.125).tolist()): # reversed(range(*self.clkfbout_mult_frange)):
                # if clkfbout_mult == 102.625 and divclk_divide == 7:
                #     import pdb; pdb.set_trace()
                # print (clkfbout_mult, divclk_divide)
                all_valid = True
                vco_freq = self.clkin_freq*clkfbout_mult/divclk_divide
                breakpoint
                (vco_freq_min, vco_freq_max) = self.vco_freq_range
                if (vco_freq >= vco_freq_min*(1 + self.vco_margin) and
                    vco_freq <= vco_freq_max*(1 - self.vco_margin)):
                    for n, (clk, f, p, m) in sorted(self.clkouts.items()):
                        # import pdb; pdb.set_trace()
                        valid = False
                        d_ranges = [self.clkout_divide_range]
                        if getattr(self, "clkout{}_divide_range".format(n), None) is not None:
                            d_ranges += [getattr(self, "clkout{}_divide_range".format(n))]
                            
                        if n == 0:
                            for d in np.arange(2, 128.1, 0.125).tolist():
                                clk_freq = vco_freq/d
                                if abs(clk_freq - f) <= f*m:
                                    config["clkout{}_freq".format(n)]   = clk_freq
                                    config["clkout{}_divide".format(n)] = d
                                    config["clkout{}_phase".format(n)]  = p
                                    valid = True
                                    break
                                if valid:
                                    break
                        else:
                            for d_range in d_ranges:
                                for d in clkdiv_range(*d_range):
                                    clk_freq = vco_freq/d
                                    if abs(clk_freq - f) <= f*m:
                                        config["clkout{}_freq".format(n)]   = clk_freq
                                        config["clkout{}_divide".format(n)] = d
                                        config["clkout{}_phase".format(n)]  = p
                                        valid = True
                                        break
                                    if valid:
                                        break
                        if not valid:
                            all_valid = False
                else:
                    all_valid = False
                if all_valid:
                    config["vco"]           = vco_freq
                    config["clkfbout_mult"] = clkfbout_mult
                    compute_config_log(self.logger, config)
                    # import pdb; pdb.set_trace()
                    return config
        raise ValueError("No PLL config found")

class USPIDELAYCTRL(LiteXModule):
    def __init__(self, cd_ref, cd_sys, reset_cycles=64, ready_cycles=64):
        self.cd_ic = ClockDomain()
        ic_reset_counter = Signal(max=reset_cycles, reset=reset_cycles-1)
        ic_reset         = Signal(reset=1)
        cd_ref_sync      = getattr(self.sync, cd_ref.name)
        cd_ref_sync += [
            If(ic_reset_counter != 0,
                ic_reset_counter.eq(ic_reset_counter - 1)
            ).Else(
                ic_reset.eq(0)
            )
        ]
        ic_ready_counter = Signal(max=ready_cycles, reset=ready_cycles-1)
        ic_ready         = Signal()
        self.comb += self.cd_ic.clk.eq(cd_sys.clk)
        self.sync.ic += [
            cd_sys.rst.eq(1),
            If(ic_ready,
                If(ic_ready_counter != 0,
                    ic_ready_counter.eq(ic_ready_counter - 1)
                ).Else(
                    cd_sys.rst.eq(0)
                )
            )
        ]
        self.specials += [
            Instance("IDELAYCTRL",
                p_SIM_DEVICE = "ULTRASCALE",
                i_REFCLK     = cd_ref.clk,
                i_RST        = ic_reset,
                o_RDY        = ic_ready),
            AsyncResetSynchronizer(self.cd_ic, ic_reset)
        ]
