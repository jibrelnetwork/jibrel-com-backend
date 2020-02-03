from eth_keys import KeyAPI


def public_key_to_address(public_key: str) -> str:
    pub_key = KeyAPI.PublicKey(bytearray.fromhex(public_key.replace('0x', '')))
    return pub_key.to_address()
