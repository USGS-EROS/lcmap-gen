from cytoolz import assoc, partial
import firebird as fb
import merlin

red = ''
green = ''
blue = ''
nir = ''
swir1 = ''
swir2 = ''
thermal = ''
quality = ''
dem = ''
trends = ''
aspect = ''
mpw = ''
posidex = ''


def specs(**kwargs):
    """ Retrieve chip specs
    Args:
        specs.queries (dict): chip spec queries
        merlin.cfg    (dict): merlin configuration
    Returns:
        specs: dict
    """ 
    q   = kwargs['specs.queries']
    cfg = kwargs['merlin.cfg']
    fn  = cfg['specs.fn']
    s   = tuple(map(partial(fn, **cfg), q))

    return assoc(kwargs, 'specs', s)


def create(acquired, bounds, ubids, cfg=fb.MERLIN_CFG):
    return merlin.create(acquired=acquired, bounds=bounds, ubids=ubids, **cfg)


def ard(acquired, bounds):

    dates_fn = partial(f.chexists,
                       check_fn=timeseries.symmetric_dates,
                       keys=['quality'])

    cfg = assoc(fb.MERLIN_CFG, 'dates_fn', dates_fn)
    
    query = {'red': red,
             'green': green,
             'blue': blue,
             'nir': nir,
             'swir1': swir1,
             'swir2': swir2, 
             'thermal': thermal,
             'quality': quality}

    return create(acquired=acquired,
                  bounds=bounds,
                  ubids=ubids(specs(query)),
                  cfg=cfg))


def aux(acquired, bounds):

    query = {'dem': dem,
             'trends': trends,
             'aspect': aspect,
             'mpw': mpw,
             'posidex': posidex}

    return create(acquired, bounds, ubids(specs(query)))