from __future__ import absolute_import, division, print_function, unicode_literals
import logging
import abc

from astropy.utils.misc import InheritDocstrings

from ...extern import six
from .iminuit import fit_iminuit, _get_covar
from .sherpa import fit_sherpa


__all__ = ["Fit"]

log = logging.getLogger(__name__)


class FitMeta(InheritDocstrings, abc.ABCMeta):
    pass


@six.add_metaclass(FitMeta)
class Fit(object):
    """Abstract Fit base class.
    """
    @abc.abstractmethod
    def total_stat(self, parameters):
        """Total likelihood given the current model parameters"""
        pass

    def fit(self, optimizer="minuit", opts_minuit=None):
        """Run the fit

        Parameters
        ----------
        optimizer : {"minuit", "levmar", "simplex", "moncar", "gridsearch"}
            Which optimizer to use. See https://iminuit.readthedocs.io for details
            on the the option `"minuit"`.
            See http://cxc.cfa.harvard.edu/sherpa/methods/index.html for details
            on the other methods.
        opts_minuit : dict (optional)
            Options passed to `iminuit.Minuit` constructor

        Returns
        -------
        fit_result : `FitResult`
            Fit result object with the fit results.
        """
        parameters = self._model.parameters

        if parameters.apply_autoscale:
            parameters.autoscale()

        if optimizer == 'minuit':
            result = fit_iminuit(
                parameters=parameters,
                function=self.total_stat,
                opts_minuit=opts_minuit,
            )
            # As a preliminary solution we attach the Minuit object to the Fit
            # class as a hidden attribute, so that it becomes available to the
            # user
            self._minuit = result.pop("minuit")
        elif optimizer in ["levmar", "simplex", "moncar", "gridsearch"]:
            result = fit_sherpa(
                parameters=parameters,
                function=self.total_stat,
                optimizer=optimizer,
            )
        else:
            raise ValueError("{} is not a valid optimizer.",format(optimizer))

        # Copy final results into the parameters object
        parameters.set_parameter_factors(result.pop("factors"))

        result["model"] = self._model.copy()
        result["total_stat"] = self.total_stat(self._model.parameters)
        result["optimizer"] = optimizer
        return result

    # TODO: this is a preliminary solution to restore the old behaviour
    def _estimate_errors(self, fit_result):
        parameters = fit_result.model.parameters

        if self._minuit.covariance is not None:
            parameters.set_covariance_factors(_get_covar(self._minuit))
        else:
            log.warning("No covariance matrix found")
            parameters.covariance = None
        return fit_result

    def run(self, steps="all", opts_minuit=None):
        """
        Run all fitting steps.

        Parameters
        ----------
        opts_minuit : dict (optional)
            Options passed to `iminuit.Minuit` constructor

        """
        if steps == "all":
            steps = ["fit", "errors"]

        if "fit" in steps:
            result = self.fit(opts_minuit=opts_minuit)

        if "errors" in steps:
            result = self._estimate_errors(result)

        return result
