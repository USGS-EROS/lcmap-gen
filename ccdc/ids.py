from pyspark.sql import SparkSession
from pyspark.sql.types import IntegerType
from pyspark.sql.types import StructField
from pyspark.sql.types import StructType

import ccdc


def chip_schema():
    """Schema for ids dataframe"""
    
    return StructType([StructField('cx', IntegerType(), nullable=False),
                       StructField('cy', IntegerType(), nullable=False)])


def tile_schema():
    """Schema for tile ids dataframe"""

    return StructType([StructField('tx', IntegerType(), nullable=False),
                       StructField('ty', IntegerType(), nullable=False)])


def rdd(ctx, xys, chunk_size=1):
    """Creates rdd of xy ids
    
    Args:
        ctx             : spark context
        xys  (sequence): ((x1,y1),(x2,y2),(x3,y3)...))

    Returns:
        RDD of ids
    """

    log = ccdc.logger(ctx, __name__)

    log.info('loading {} ids...'.format(len(xys)))
    log.debug('xys datatype:{}'.format(type(xys)))
    log.trace('xys:{}'.format(xys))
    
    return ctx.parallelize(xys, chunk_size)
     
    
def dataframe(ctx, rdd, schema):
    """Creates dataframe matching 'schema'
 
    Args:
        ctx: spark context
        rdd: ids.rdd
        schema: schema for ids

    Returns:
        dataframe conforming to schema
    """

    return SparkSession(ctx).createDataFrame(rdd, schema)
