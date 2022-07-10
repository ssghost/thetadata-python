"""Contains core datatypes."""
from __future__ import annotations
from datetime import datetime, timedelta, date
from tqdm import tqdm

# from pydantic.dataclasses import dataclass
from dataclasses import dataclass
import enum
import pandas as pd
from pandas import DataFrame, Series
from .exceptions import EnumParseError, ResponseError


@enum.unique
class DataType(enum.Enum):
    """Codes used in the format tick to ID the type of data in the body ticks."""

    DATE = 0  # (, 0)
    MS_OF_DAY = 1  # (, 0)
    CORRECTION = 2  # (, 0)
    PRICE_TYPE = 4  # (, -1)

    # QUOTES
    BID_SIZE = 101  # (, 1)
    BID_EXCHANGE = 102  # (, 2)
    BID = 103  # (, 3, true)
    BID_CONDITION = 104  # (, 4)
    ASK_SIZE = 105  # (, 5)
    ASK_EXCHANGE = 106  # (, 6)
    ASK = 107  # (, 7, true)
    ASK_CONDITION = 108  # (, 8)

    # PRICING
    MIDPOINT = 111  # (, 1)
    VWAP = 112  # (, 2)
    QWAP = 113  # (, 3)
    WAP = 114  # (, 4)

    # OPEN INTEREST
    OPEN_INTEREST = 121  # (, 1)

    # TRADES
    PRICE = 131  # (, 1)
    SIZE = 132  # (, 2)
    CONDITION = 133  # (, 3)

    # VOLUME
    VOLUME = 141  # (, 1)
    COUNT = 142  # (, 2)

    # FIRST ORDER GREEKS
    THETA = 151  # (, 1)
    VEGA = 152  # (, 2)
    DELTA = 153  # (, 3)
    RHO = 154  # (, 4)
    EPSILON = 155  # (, 5)
    LAMBDA = 156  # (, 6)

    # SECOND ORDER GREEKS
    GAMMA = 161  # (, 1)
    VANNA = 162  # (, 2)
    CHARM = 163  # (, 3)
    VOMMA = 164  # (, 4)
    VETA = 165  # (, 5)
    VERA = 166  # (, 6)
    SOPDK = 167  # (, 7)

    # THIRD ORDER GREEKS
    SPEED = 171  # (, 1)
    ZOMMA = 172  # (, 2)
    COLOR = 173  # (, 3)
    ULTIMA = 174  # (, 4)

    # OTHER CALCS
    D1 = 181  # (, 1)
    D2 = 182  # (, 1)
    DUAL_DELTA = 183  # (, 3)
    DUAL_GAMMA = 184  # (, 4)

    # OHLC
    RATE = 191  # (, 1)
    OPEN = 192  # (, 2)
    HIGH = 193  # (, 3)
    LOW = 194  # (, 4)
    CLOSE = 195  # (, 5)

    # IMPLIED VOLATILITY
    IMPLIED_VOL = 201  # (, 1)

    # OTHER
    RATIO = 211  # (, 1)
    RATING = 212  # (, 2)
    LIST = 213  # (, 3)

    @classmethod
    def from_code(cls: DataType, code: int) -> DataType:
        """Create a DataType by its associated code.

        :raises EnumParseError: If the code does not match a DataType
        """
        for member in cls:
            if code == member.value:
                return member
        raise EnumParseError(code, cls)

    def is_price(self) -> bool:
        """Check if this DataType indicates a price."""
        return self == DataType.BID


@enum.unique
class MessageType(enum.Enum):
    """Codes used to ID types of requests/responses."""

    # Internal client communication
    CREDENTIALS = 0
    SESSION_TOKEN = 1
    INFO = 2
    METADATA = 3
    CONNECTED = 4

    # API communication
    PING = 100
    ERROR = 101
    DISCONNECTED = 102
    RECONNECTED = 103
    REQ_SYMS = 104
    SET_SYMS = 105
    CANT_CHANGE_SYMS = 106
    CHANGED_SYMS = 107

    # Client data
    HIST = 200
    ALL_EXPIRATIONS = 201
    ALL_STRIKES = 202
    HIST_END = 203
    LAST_QUOTE = 204
    ALL_ROOTS = 205
    LIST_END = 206

    # Experimental
    REQUEST_SERVER_LIST = 300
    REQUEST_OPTIMAL_SERVER = 301
    OPTIMAL_SERVER = 302
    PACKET = 303
    BAN_IP = 304
    POPULATION = 305

    @classmethod
    def from_code(cls: MessageType, code: int) -> MessageType:
        """Create a MessageType by its associated code.

        :raises EnumParseError: If the code does not match a MessageType
        """
        for member in cls:
            if code == member.value:
                return member
        raise EnumParseError(code, cls)


@enum.unique
class SecType(enum.Enum):
    """Security types."""

    OPTION = "OPTION"
    STOCK = "STOCK"
    FUTURE = "FUTURE"
    FORWARD = "FORWARD"
    SWAP = "SWAP"
    DEBT = "DEBT"
    CRYPTO = "CRYPTO"
    WARRANT = "WARRANT"


@enum.unique
class OptionRight(enum.Enum):
    """Option rights."""

    PUT = "P"
    CALL = "C"


@enum.unique
class OptionReqType(enum.Enum):
    """Option request type codes."""

    # VALUE
    DEFAULT = 100
    QUOTE = 101
    VOLUME = 102
    OPEN_INTEREST = 103

    # STANDARD
    LIQUIDITY = 201
    LIQUIDITY_PLUS = 202
    IMPLIED_VOLATILITY = 203
    GREEKS = 204
    OHLC = 205

    # PRO
    TRADE = 301
    TRADE_GREEKS = 302
    GREEKS_SECOND_ORDER = 303
    GREEKS_THIRD_ORDER = 304
    ALT_CALCS = 305


@dataclass
class DateRange:
    """Represents an inclusive date range."""

    start: date
    end: date

    def __init__(self, start: date, end: date):
        self.start = start
        self.end = end
        assert (
            start <= end
        ), f"Start date {self.start} cannot be greater than end date {self.end}!"

    @classmethod
    def from_days(cls, n: int) -> DateRange:
        """Create a date range that spans the past n days."""
        assert type(n) == int
        assert n >= 0, "n must be nonnegative"
        end = datetime.now().date()
        start = end - timedelta(days=n)
        return cls(start, end)


@dataclass
class Header:
    """Represents the header returned on every Terminal call."""

    message_type: MessageType
    id: int
    latency: int
    error: int
    format_len: int
    size: int

    @classmethod
    def parse(cls, data: bytes) -> Header:
        """Parse binary header data into an object.

        :param data: raw header data, 20 bytes long
        """
        assert (
            len(data) == 20
        ), f"Cannot parse header with {len(data)} bytes. Expected 20 bytes."
        # avoid copying header data when slicing
        data = memoryview(data)
        """
        Header format:
            bytes | field
                2 | message type
                8 | id
                2 | latency
                2 | error
                1 | reserved / special
                1 | format length
                4 | size
        """
        parse_int = lambda d: int.from_bytes(d, "big")
        # parse
        msgtype = MessageType.from_code(parse_int(data[:2]))
        id = parse_int(data[2:10])
        latency = parse_int(data[10:12])
        error = parse_int(data[12:14])
        format_len = data[15]
        size = parse_int(data[16:20])
        return cls(
            message_type=msgtype,
            id=id,
            latency=latency,
            error=error,
            format_len=format_len,
            size=size,
        )


def _check_body_errors(header: Header, body_data: bytes):
    """Check for errors from the Terminal.

    :raises ResponseError: if the header indicates an error, containing a helpful error message."""
    if header.message_type == MessageType.ERROR:
        msg = body_data.decode("ascii")
        raise ResponseError(msg)


# map price types to price multipliers
_pt_to_price_mul = [
    0,
    0.000000001,
    0.00000001,
    0.0000001,
    0.000001,
    0.00001,
    0.0001,
    0.001,
    0.01,
    0.1,
    1,
    10.0,
    100.0,
    1000.0,
    10000.0,
    100000.0,
    1000000.0,
    10000000.0,
    100000000.0,
    1000000000.0,
]


class TickBody:
    """Represents the body returned on Terminal calls that deal with ticks."""

    def __init__(self, ticks: DataFrame):
        assert isinstance(
            ticks, DataFrame
        ), "Cannot initialize body bc ticks is not a DataFrame"
        self.ticks: DataFrame = ticks

    @classmethod
    def parse(
        cls, header: Header, data: bytes, progress_bar: bool = False
    ) -> TickBody:
        """Parse binary body data into an object.

        :param header: parsed header data
        :param data: the binary response body
        :param: progress_bar: Print a progress bar displaying progress.
        """
        assert (
            len(data) == header.size
        ), f"Cannot parse body with {len(data)} bytes. Expected {header.size} bytes."
        _check_body_errors(header, data)

        # avoid copying body data when slicing
        data = memoryview(data)
        parse_int = lambda d: int.from_bytes(d, "big")

        # parse ticks
        n_ticks = int(header.size / (header.format_len * 4))
        bytes_per_tick = header.format_len

        # parse format tick
        format_tick_codes = []
        for b in range(bytes_per_tick):
            int_ = parse_int(data[b * 4 : b * 4 + 4])
            format_tick_codes.append(int_)
        format: list[DataType] = list(
            map(lambda code: DataType.from_code(code), format_tick_codes)
        )

        # initialize empty dataframe w/ format columns
        df = pd.DataFrame(columns=format)

        # get the index of the price type column if it exists
        if DataType.PRICE_TYPE in df.columns:
            price_type_idx = df.columns.get_loc(DataType.PRICE_TYPE)

        # parse the rest of the ticks
        ticks = []
        for tn in tqdm(
            range(1, n_ticks), desc="Processing", disable=not progress_bar
        ):
            tick_offset = tn * bytes_per_tick * 4
            tick = []
            for b in range(bytes_per_tick):
                # parse int
                int_offset = tick_offset + b * 4
                int_ = parse_int(data[int_offset : int_offset + 4])
                tick.append(int_)

            # map price columns to prices if the tick contains a price type
            if price_type_idx is not None:
                # get price multiplier from price type
                pt = tick[price_type_idx]
                price_multiplier = _pt_to_price_mul[pt]
                # multiply tick price fields by price multiplier
                for i in range(len(tick)):
                    if format[i].is_price():
                        tick[i] = tick[i] * price_multiplier
                # remove price type from tick
                del tick[price_type_idx]

            ticks.append(tick)

        # delete price type column if it exists
        if price_type_idx is not None:
            del df[DataType.PRICE_TYPE]

        # add ticks to dataframe in a single concat
        df = pd.concat(
            [pd.DataFrame(ticks, columns=df.columns), df],
            ignore_index=True,
        )

        return cls(ticks=df)


class ListBody:
    """Represents the body returned on every Terminal call that have one DataType."""

    def __init__(self, lst: Series):
        assert isinstance(
            lst, Series
        ), "Cannot initialize body bc lst is not a Series"
        self.lst: Series = lst

    @classmethod
    def parse(
        cls, header: Header, data: bytes, progress_bar: bool = False
    ) -> ListBody:
        """Parse binary body data into an object.

        :param header: parsed header data
        :param data: the binary response body
        :param: progress_bar: Print a progress bar displaying progress.
        """
        assert (
            len(data) == header.size
        ), f"Cannot parse body with {len(data)} bytes. Expected {header.size} bytes."
        _check_body_errors(header, data)

        lst = data.decode("ascii").split(",")
        lst = pd.Series(lst, copy=False)

        return cls(lst=lst)