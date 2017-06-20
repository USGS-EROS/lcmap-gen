from firebird import ccd_params
from firebird import dates as fd
from firebird import functions as f
from firebird import inputs
from firebird import logger
from firebird import products as fp
from functools import partial
from functools import wraps
import ccd
import inspect


# TODO: try/except calls to run products in product functions.

def algorithm(name, version):
    """Standardizes algorithm name and version representation.
    :param name: Name of algorithm
    :param version: Version of algorithm
    :return: name_version
    """
    return '{}_{}'.format(name, version)


def prerr(v, x, y, e, date):
    """Intercepts calls to rdd transformations, checks for previous errors and
    returns a default error message for the function rather than executing it.
    Parameters allow dynamic mapping to x, y, errors and date elements within
    RDDs of different shape.
    :param v: Version of the wrapped function.  Included in resulting RDD
    :param x: Index of the x coordinate in the input RDD
    :param y: Index of the y coordinate in the input RDD
    :param e: Index of the errors element in the input RDD
    :param date: Index of the datestr in the input RDD which will be included
                  in the output RDD.
    :return: Either a properly formatted RDD tuple or the result of executing
             the RDD function.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(rdd):
            err = f.extract(rdd, e)
            if err is not None:
                x = f.extract(rdd, x)
                y = f.extract(rdd, y)
                d = f.extract(rdd, date)
                a = algorithm(func.__name__, ver)
                err = 'previous-error[{}]:{}'.format(rdd.getName(), err)
                # return properly formatted RDD with no result and an error
                return (key(x, y, a, d), None, err)
            else:
                return func(rdd)
        return wrapper
    return decorator


def currerr(v, x, y, e, data):
    def decorator(func):
        @wraps(func)
        def wrapper(rdd):
            try:
                return func(rdd)
            except Exception as errors:
                x = f.extract(rdd, x)
                y = f.extract(rdd, y)
                d = f.extract(rdd, date)
                a = algorithm(func.__name__, v)
                logger.error("{}".format(func.__name__))
                return ((x, y, a, d), None, errors)


def guard(record_index):
    def decorator(func):
        @wraps(func)
        def wrapper(rdd):
            return preverr(rdd) or tryexcept(func, rdd)



def simplify_detect_results(results):
    """Convert child objects inside CCD results from NamedTuples to dicts"""
    output = dict()
    for key in results.keys():
        output[key] = f.simplify_objects(results[key])
    return output


def result_to_models(result):
    """Function to extract the change_models dictionary from the CCD results
    :param result: CCD result object (dict)
    :return: list
    """
    #raise Exception("JSONING:{}".format(result))
    return simplify_detect_results(result)['change_models']


@preverr(v=ccd.algorithm, x=(0, 0), y=(0, 0), date=(0, 3), err=(2,))
@currerr(v=ccd.algorithm, x=(0, 0), y=(0, 0), err=(0, 3), data=(1,))
def pyccd(rdd):
    """Execute ccd.detect
    :param rdd: Tuple of (tuple, dict) generated from pyccd_inputs
                ((x, y, algorithm, datestring): data)
    :return: A tuple of (tuple, dict) with pyccd results
             ((x, y, algorithm, acquired), results, errors)
    """
    x = rdd[0][0]
    y = rdd[0][1]
    acquired = rdd[0][3]
    data = rdd[1]
    #  errors = rdd[2]
    try:
        results = ccd.detect(dates=data['dates'],
                             blues=data['blues'],
                             greens=data['greens'],
                             reds=data['reds'],
                             nirs=data['nirs'],
                             swir1s=data['swir1s'],
                             swir2s=data['swir2s'],
                             thermals=data['thermals'],
                             quality=data['quality'],
                             params=ccd_params())
    except Exception as errors:
        logger.error("Exception running ccd.detect: {}".format(errors))
        return ((x, y, ccd.algorithm, acquired), None, errors)
    else:
        return ((x, y, ccd.algorithm, acquired), results, None)

key=(0, 0), data=(0, 1), errs=(0, 2), date=(1)

@preverr(v=fp.version, x=(0, 0, 0), y=(0, 0, 1), date=(1,), err=(0, 2))
@currerr(v=fp.version, x=(0, 0, 0), y=(0, 0, 1), data=(0, 1), err=(0, 2))
def lastchange(rdd):
    """Create lastchange product
    :param rdd: (((x, y, algorithm, acquired), data, errors), product_date)
    :return: ((x, y, algorithm, result, errors))
    """
    x = rdd[0][0][0]
    y = rdd[0][0][1]
    data = rdd[0][1]
    date = fd.to_ordinal(rdd[1])
    alg = algorithm(inspect.stack()[0][3], fp.version)
    try:
        return ((x, y, alg, rdd[1]),
                fp.lastchange(result_to_models(data), ord_date=date), None)
    except Exception as errors:
        logger.errors("Exception running lastchange:{}".format(errors))
        return ((x, y, alg, rdd[1]), None, errors)


@preverr(v=fp.version, x=(0, 0, 0), y=(0, 0, 1), date=(1,), err=[0, 2])
def changemag(rdd):
    """Create changemag product
    :param rdd: (((x, y, algorithm, acquired), data, errors), product_date)
    :return: ((x, y, algorithm, result))
    """
    x = rdd[0][0][0]
    y = rdd[0][0][1]
    data = rdd[0][1]
    date = fd.to_ordinal(rdd[1])
    alg = algorithm(inspect.stack()[0][3], fp.version)
    return ((x, y, alg, rdd[1]),
            fp.changemag(result_to_models(data), ord_date=date))


@preverr(ver=fp.version, xidx=(0, 0, 0), yidx=(0, 0, 1), didx=(1,), eidx=(0, 2))
def changedate(rdd):
    """Create changedate product
    :param rdd: (((x, y, algorithm, acquired), data, errors), product_date)
    :return: ((x, y, algorithm, result))
    """
    x = rdd[0][0][0]
    y = rdd[0][0][1]
    data = rdd[0][1]
    date = fd.to_ordinal(rdd[1])
    alg = algorithm(inspect.stack()[0][3], fp.version)
    return ((x, y, alg, rdd[1]),
            fp.changedate(result_to_models(data), ord_date=date))


@preverr(ver=fp.version, xidx=(0, 0, 0), yidx=(0, 0, 1), didx=(1,), eidx=(0, 2))
def seglength(rdd):
    """Create seglength product
    :param rdd: (((x, y, algorithm, acquired), data, errors), product_date)
    :return: ((x, y, algorithm, result))
    """
    x = rdd[0][0][0]
    y = rdd[0][0][1]
    data = rdd[0][1]
    date = fd.to_ordinal(rdd[1])
    bot = fd.to_ordinal(fd.startdate(rdd[0][0][3]))
    alg = algorithm(inspect.stack()[0][3], fp.version)
    return ((x, y, alg, rdd[1]),
            fp.seglength(result_to_models(data), ord_date=date, bot=bot))


@preverr(ver=fp.version, xidx=(0, 0, 0), yidx=(0, 0, 1), didx=(1,), eidx=(0, 2))
def curveqa(rdd):
    """Create curveqa product
    :param rdd: (((x, y, algorithm, acquired), data, errors), product_date)
    :return: ((x, y, algorithm, result))
    """
    x = rdd[0][0][0]
    y = rdd[0][0][1]
    data = rdd[0][1]
    date = fd.to_ordinal(rdd[1])
    alg = algorithm(inspect.stack()[0][3], fp.version)
    return ((x, y, alg, rdd[1]),
            fp.curveqa(result_to_models(data), ord_date=date))


def fits_in_box(value, bbox):
    """Determines if a point value fits within a bounding box (edges inclusive)
    Useful as a filtering function with conditional enforcement.
    If bbox is None then fits_in_box always returns True

    :param value: Tuple: ((x,y), (data))
    :param bbox: dict with keys: ulx, uly, lrx, lry
    :return: Boolean
    """
    def fits(point, bbox):
        x, y = point
        return (float(x) >= float(bbox['ulx']) and
                float(x) <= float(bbox['lrx']) and
                float(y) >= float(bbox['lry']) and
                float(y) <= float(bbox['uly']))

    return bbox is None or fits(value[0], bbox)


def labels(inputs=None, ccd=None, lastchange=None, changemag=None,
           changedate=None, seglength=None, curveqa=None):
    """Applies friendly names to products
    :param inputs: Inputs rdd
    :param ccd: CCD rdd
    :param lastchange: Lastchange rdd
    :param changemag: Changemag rdd
    :param changedate: Changedate rdd
    :param seglength: Seglength rdd
    :param curvaqa: Curveqa rdd
    :return: A dict of label:rdd
    """
    return {'inputs': inputs, 'ccd': ccd, 'lastchange': lastchange,
            'changemag': changemag, 'changedate': changedate,
            'seglength': seglength, 'curveqa': curveqa}


def products(jobconf, sparkcontext):
    """Product graph for firebird products
    :param jobconf: dict of broadcast variables
    :param sparkcontext: Configured spark context or None
    :return: dict keyed by product with lazy RDD as value
    """

    jc = jobconf
    sc = sparkcontext

    _chipids = sc.parallelize(jc['chip_ids'].value,
                              jc['initial_partitions'].value)\
                              .setName("CHIP IDS")

    # query data and transform it into pyccd input format
    _in = _chipids.map(partial(inputs.pyccd,
                               specs_url=jc['specs_url'].value,
                               specs_fn=jc['specs_fn'].value,
                               chips_url=jc['chips_url'].value,
                               chips_fn=jc['chips_fn'].value,
                               acquired=jc['acquired'].value,
                               queries=jc['chip_spec_queries'].value))\
                               .flatMap(lambda x: x)\
                               .filter(partial(fits_in_box,
                                               bbox=jc['clip_box'].value))\
                               .map(lambda x: ((x[0][0], x[0][1],
                                                'inputs',
                                                jc['acquired'].value),
                                                x[1]))\
                               .repartition(jc['product_partitions'].value)\
                               .setName('pyccd_inputs')

    _ccd = _in.map(pyccd).setName(ccd.algorithm).persist()

    # cartesian will create an rdd that looks like:
    # (((x, y, algorithm, product_date_str), data), product_date)
    _ccd_dates = _ccd.cartesian(sc.parallelize(jc['product_dates'].value))

    _lc = _ccd_dates.map(lastchange).setName('lastchange_v1')
    _cm = _ccd_dates.map(changemag).setName('changemag_v1')
    _cd = _ccd_dates.map(changedate).setName('changedate_v1')
    _sl = _ccd_dates.map(seglength).setName('seglength_v1')
    _qa = _ccd_dates.map(curveqa).setName('curveqa_v1')

    return labels(inputs=_in, ccd=_ccd, lastchange=_lc, changemag=_cm,
                  changedate=_cd, seglength=_sl, curveqa=_qa)


def train(product_graph, sparkcontext):
    # training_chipids()
    # requires ancillary data such as DEM, trends, et. al.
    #
    # TODO: This might require switching to the dataframe api and the
    # spark cassandra connector, especially if we are going to train on results
    # that already exist in cassandra.  Don't implement this without a
    # significant amount of hammock and whiteboard time.
    #
    # In order to send in appropriate chip ids to init, it will have
    # to accept chip ids instead of bounds and the bounds to chip id
    # determination will have to be done by whatever calls it.  This will
    # be necessary as training requires additional areas besides the area
    # one is actually attempting to train on.
    pass


def classify(product_graph, sparkcontext):
    # Same as the training graph.  This cannot run unless
    # #1 - There are ccd results and
    # #2 - The classifier has been trained.
    # Dont just jam these two things into this rdd graph setup.  Find the
    # cleanest way to represent and handle it.  It might require running
    # ccd first, training second and classification third.  Or they might all
    # be able to be put into the same graph and run at the same time.
    #
    # Regardless, all this data will need to be persisted so after its all
    # working we will probably need the ability to load data from iwds,
    # determine what else is needed (what areas are missing based on the
    # request) conditionally produce it, then proceed with the operations
    pass
