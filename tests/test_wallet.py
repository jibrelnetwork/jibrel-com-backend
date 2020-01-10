import uuid

import pytest

from jibrel.wallets.models import Wallet


def get_payload(**overrides):
    wallet = {
        'name': 'wallet 1',
        'uid': uuid.uuid4().hex,
        'mnemonic': 'ABCD',
        'public_key': 'dcba',
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
        'uid': obj.uid,
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

    expected = {'version_number': 1}
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

    assert response.status_code == 400
    assert response.data == {'errors': {'uid': [{'message': 'wallet with this uid already exists.', 'code': 'unique'}]}}


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
            'uid': required,
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
    assert response.data['uid'] == wallet.uid
    assert response.data['mnemonic'] == wallet.mnemonic
    assert response.data['name'] == wallet.name
    assert response.data['public_key'] == wallet.public_key
    assert response.data['derivation_path'] == wallet.derivation_path


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
               'uid': wallet.uid,
               'mnemonic': 'ABCD up',
               'public_key': 'dcba up',
               'derivation_path': 'xyz up',
               'version_number': 100
               }
    response = client.put(
        f'/v1/wallets/{wallet.uid}/',
        payload,
        content_type='application/json'
    )

    wallet_up = Wallet.objects.get(pk=wallet.pk)

    assert response.status_code == 200
    assert wallet_up.uid == wallet.uid
    assert wallet_up.name == 'wallet up'
    assert response.data['mnemonic'] == payload['mnemonic']
    assert response.data['public_key'] == payload['public_key']
    assert response.data['derivation_path'] == payload['derivation_path']
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
               'public_key': 'dcba up',
               'derivation_path': 'xyz up',
               'version_number': 100
               }
    response = client.put(
        f'/v1/wallets/{wallet.uid}/',
        payload,
        content_type='application/json'
    )

    assert response.status_code == 400
    assert response.data ==  {'errors': {'uid': [{'message': "Can't change Wallet UID", 'code': 'invalid'}]}}
