from sqlalchemy import BigInteger, Integer

BigIntType = BigInteger().with_variant(Integer, "sqlite")
