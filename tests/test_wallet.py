import itertools
from unittest.mock import ANY

import pytest

from jibrel.wallets.models import Wallet


PUBLIC_KEYS = itertools.cycle([
    '0xc681355e28d317b7cc4eb0860e0a01491bcff2a03284fd5f1f92909da9fc5a3e14cfa756da9498c6f0902fae1a6ea2185eda7d8a666b9a5724e65a39d1eb052f',
    '0xa8e5d9ba5975972f58151b2c0c619884c601c1ff8761854afc08245ca9c698edfe3cbe67dcb0da133138c24a212b95498860a2f617bf2075a2ee862c21d93669',
    '0x26b35cd5fd103e25b4d0fcc349e855cd674744e3c95856b9b07b2b02a251d59153376d569a951029fb80550deb8d9b888fd6859f51d28c3f4169d0b7a7970c1b',
    '0x11d0d73391e4013ad72ab539fc16709b808a8df6f2540df3c75622d371088d565c4f29af3f2ffc01a1c3856d2a4bede79854cc5d0f07b583adf0b8952ec56968',
    '0x5c0c99ad88e104699925a772490919efc60dfdd9f8739eca236e7ef7a1ad1e2b30138ae4c000925d764de437eeff3aa8b9c4a00cb3590dd5c940d3493e523ead',
    '0x794c9cc705634e8cdc307dde35be60646a6498a5d51169e4f3a19c6135159d8a26c567dac07c6c5d0df57974890f5bf79743624c2332d668c9196bb71652b82c'
])

ADDRESSES = itertools.cycle([
    '0xF18aa17F72FDa4a27f25b31df1aDF87eBd6Bb396',
    '0x7CF260A280DDA1ED9e809519bDFf08AA10e80b23',
    '0x3C7d00c27737590A50B1C67C7BF53eEEB1BAB81c',
    '0xC26C534A4A6574083dd1D3Dc79cf340eB8c7342f',
    '0x15461e833e7F1f9DDC5722a1BC14A609983EdB07',
    '0x3BC452D29262A85e7F150f09f6E2E6B7b290e456',
])


def get_payload(**overrides):
    wallet = {
        'name': 'wallet 1',
        'mnemonic': 'ABCD',
        'public_key': next(PUBLIC_KEYS),
        'derivation_path': 'xyz'
    }
    wallet.update(overrides)
    return wallet


def add_wallet(user, **overrides):
    data = get_payload(**overrides)
    data['user'] = user
    return Wallet.objects.create(**data)


def wallet_data(obj):
    return {
        'name': obj.name,
        'uid': str(obj.uid),
        'mnemonic': obj.mnemonic,
        'public_key': obj.public_key,
        'derivation_path': obj.derivation_path,
        'version_number': obj.version_number,
    }


@pytest.mark.django_db
def test_wallet_create(
    client,
    user_with_confirmed_phone,
):
    payload = get_payload()
    client.force_login(user_with_confirmed_phone)
    response = client.post(
        '/v1/wallets/',
        payload,
        content_type='application/json'
    )

    expected = {'version_number': 1, 'uid': ANY}
    expected.update(payload)
    assert response.status_code == 201
    assert response.data == expected


@pytest.mark.django_db
def test_wallet_create_not_uniq(
    client,
    user_with_confirmed_phone,
    user_not_confirmed_factory,
):
    user2 = user_not_confirmed_factory()
    w = add_wallet(user2, name='X')
    payload = get_payload(uid=w.uid)
    client.force_login(user_with_confirmed_phone)
    response = client.post(
        '/v1/wallets/',
        payload,
        content_type='application/json'
    )

    assert response.status_code == 201
    assert response.data['name'] == 'wallet 1'


@pytest.mark.django_db
def test_wallet_create_empty(
    client,
    user_with_confirmed_phone,
):
    payload = {}
    client.force_login(user_with_confirmed_phone)
    response = client.post(
        '/v1/wallets/',
        payload,
        content_type='application/json'
    )

    assert response.status_code == 400
    required = [{'code': 'required', 'message': 'This field is required.', 'code': 'required'}]
    assert response.data == {'errors':
        {
            'name': required,
            'mnemonic': required,
            'public_key': required,
            'derivation_path': required,
        }
    }


@pytest.mark.django_db
def test_wallet_get(
    client,
    user_with_confirmed_phone,
):
    wallet = add_wallet(user_with_confirmed_phone)
    client.force_login(user_with_confirmed_phone)
    response = client.get(
        f'/v1/wallets/{wallet.uid}/',
    )
    assert response.status_code == 200
    assert response.data['uid'] == str(wallet.pk)
    assert response.data['mnemonic'] == wallet.mnemonic
    assert response.data['name'] == wallet.name
    assert response.data['public_key'] == wallet.public_key
    assert response.data['derivation_path'] == wallet.derivation_path


@pytest.mark.django_db
def test_wallet_get_404(
    client,
    user_with_confirmed_phone,
):
    add_wallet(user_with_confirmed_phone)
    client.force_login(user_with_confirmed_phone)
    response = client.get(
        f'/v1/wallets/xxx/',
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_wallet_get_404_not_owner(
    client,
    user_with_confirmed_phone,
    user_not_confirmed_factory,
):
    user2 = user_not_confirmed_factory()
    wallet = add_wallet(user2)
    client.force_login(user_with_confirmed_phone)
    response = client.get(
        f'/v1/wallets/{wallet.uid}/',
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_wallet_list(
    client,
    user_with_confirmed_phone,
    user_not_confirmed_factory,
):
    user2 = user_not_confirmed_factory()
    wallet1 = add_wallet(user_with_confirmed_phone)
    wallet2 = add_wallet(user_with_confirmed_phone, name='wallet 2')
    add_wallet(user2, name='wallet 3')
    client.force_login(user_with_confirmed_phone)
    response = client.get(
        f'/v1/wallets/',
    )

    assert response.status_code == 200
    assert len(response.data) == 2
    assert response.data[0] == wallet_data(wallet2)
    assert response.data[1] == wallet_data(wallet1)


@pytest.mark.django_db
def test_wallet_update_partial(
    client,
    user_with_confirmed_phone,
):
    wallet = add_wallet(user_with_confirmed_phone)
    client.force_login(user_with_confirmed_phone)
    payload = {'name': 'newname', 'version_number': 42}
    response = client.patch(
        f'/v1/wallets/{wallet.uid}/',
        payload,
        content_type='application/json'
    )

    wallet_up = Wallet.objects.get(pk=wallet.pk)
    assert response.status_code == 200
    assert wallet_up.name == 'newname'
    assert wallet_up.version_number == 2


@pytest.mark.django_db
def test_wallet_update_full(
    client,
    user_with_confirmed_phone,
):
    wallet = add_wallet(user_with_confirmed_phone)
    client.force_login(user_with_confirmed_phone)
    payload = {'name': 'wallet up',
               'uid': str(wallet.pk),
               'mnemonic': 'ABCD up',
               'public_key': '0xc681355e28d317b7cc4eb0860e0a01491bcff2a03284fd5f1f92909da9fc5a3e14cfa756da9498c6f0902fae1a6ea2185eda7d8a666b9a5724e65a39d1eb052f',
               'derivation_path': 'xyz up',
               'version_number': 100
               }
    response = client.put(
        f'/v1/wallets/{wallet.uid}/',
        payload,
        content_type='application/json'
    )

    wallet_up = Wallet.objects.get(pk=wallet.pk)
    print('DDD', response.data)
    assert response.status_code == 200
    assert wallet_up.uid == wallet.uid
    assert wallet_up.name == 'wallet up'
    assert wallet_up.mnemonic == wallet.mnemonic
    assert wallet_up.public_key == wallet.public_key
    assert wallet_up.derivation_path == wallet.derivation_path
    assert wallet_up.version_number == 2


@pytest.mark.django_db
def test_wallet_update_change_uid(
    client,
    user_with_confirmed_phone,
):
    wallet = add_wallet(user_with_confirmed_phone)
    client.force_login(user_with_confirmed_phone)
    payload = {'name': 'wallet up',
               'uid': 'xxx',
               'mnemonic': 'ABCD up',
               'public_key': '0xc681355e28d317b7cc4eb0860e0a01491bcff2a03284fd5f1f92909da9fc5a3e14cfa756da9498c6f0902fae1a6ea2185eda7d8a666b9a5724e65a39d1eb052f',
               'derivation_path': 'xyz up',
               'version_number': 100
               }
    response = client.put(
        f'/v1/wallets/{wallet.uid}/',
        payload,
        content_type='application/json'
    )

    wallet_up = Wallet.objects.get(pk=wallet.pk)

    assert wallet_up.pk == wallet.pk
    assert wallet_up.name == 'wallet up'
    assert wallet_up.mnemonic == wallet.mnemonic
    assert wallet_up.public_key == wallet.public_key
    assert wallet_up.derivation_path == wallet.derivation_path
    assert wallet_up.version_number == 2
