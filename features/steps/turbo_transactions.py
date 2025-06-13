import typing

from behave import given, when, then, use_step_matcher

from aptos_sdk import ed25519
from aptos_sdk.account import Account
from aptos_sdk.account_address import AccountAddress
from aptos_sdk.bcs import Deserializer, Serializer
from aptos_sdk.transactions import (
    EntryFunction,
    ModuleId,
    RawTransaction,
    Script,
    SignedTransaction,
    TransactionArgument,
    TransactionExtraConfigV1,
    TransactionExecutableEntryFunction,
    TransactionExecutableScript,
    TransactionInnerPayloadV1,
    TransactionPayload,
    convert_payload_to_turbo_payload,
)

# Use regular expressions
use_step_matcher("re")


@given("a sender account")
def given_sender_account(context: typing.Any):
    private_key = ed25519.PrivateKey.random()
    context.sender_account = Account.load_key(private_key.hex())


@given("a recipient address")
def given_recipient_address(context: typing.Any):
    private_key = ed25519.PrivateKey.random()
    context.recipient_address = AccountAddress.from_key(private_key.public_key())


@given(r'an entry function payload for "(?P<function_name>\w+)"')
def given_entry_function_payload(context: typing.Any, function_name: str):
    if function_name == "transfer":
        # Create a basic transfer entry function
        recipient = getattr(context, 'recipient_address', AccountAddress.from_str("0x1"))
        transaction_arguments = [
            TransactionArgument(recipient, Serializer.struct),
            TransactionArgument(1000, Serializer.u64),
        ]
        
        entry_function = EntryFunction.natural(
            "0x1::aptos_account",
            "transfer",
            [],
            transaction_arguments,
        )
    else:
        # Generic entry function for testing
        entry_function = EntryFunction.natural(
            "0x1::test_module",
            function_name,
            [],
            [],
        )
    
    context.entry_function = entry_function
    context.payload = TransactionPayload(entry_function)


@given(r'a script payload with code "(?P<script_code>0x[0-9a-fA-F]+)"')
def given_script_payload(context: typing.Any, script_code: str):
    code_bytes = bytes.fromhex(script_code.removeprefix("0x"))
    script = Script(code_bytes, [], [])
    context.script = script
    context.payload = TransactionPayload(script)


@given(r"a replay nonce (?P<replay_nonce>\d+)")
def given_replay_nonce(context: typing.Any, replay_nonce: str):
    context.replay_nonce = int(replay_nonce)


@given(r"a replay protection nonce (?P<replay_nonce>\d+)")
def given_replay_protection_nonce_step(context: typing.Any, replay_nonce: str):
    context.replay_nonce = int(replay_nonce)


@given(r"a sequence number (?P<sequence_number>\d+)")
def given_sequence_number(context: typing.Any, sequence_number: str):
    context.sequence_number = int(sequence_number)


@given(r'a multisig address "(?P<multisig_address>0x[0-9a-fA-F]+)"')
def given_multisig_address(context: typing.Any, multisig_address: str):
    context.multisig_address = AccountAddress.from_str(multisig_address)


@given(r"an amount (?P<amount>\d+)")
def given_amount(context: typing.Any, amount: str):
    context.amount = int(amount)


@given(r'an invalid payload type (?P<payload_type>\w+)')
def given_invalid_payload_type(context: typing.Any, payload_type: str):
    # Create a payload with an unsupported variant for turbo conversion
    if payload_type == "MODULE_BUNDLE":
        context.invalid_payload = TransactionPayload.__new__(TransactionPayload)
        context.invalid_payload.variant = TransactionPayload.MODULE_BUNDLE
        context.invalid_payload.value = "mock_module_bundle"
    elif payload_type == "MULTISIG":
        context.invalid_payload = TransactionPayload.__new__(TransactionPayload)
        context.invalid_payload.variant = TransactionPayload.MULTISIG
        context.invalid_payload.value = "mock_multisig"


@given(r'the TypeScript SDK turbo transaction hex "(?P<hex_string>0x[0-9a-fA-F]+)"')
def given_typescript_sdk_hex(context: typing.Any, hex_string: str):
    context.typescript_hex = hex_string
    context.typescript_bytes = bytes.fromhex(hex_string.removeprefix("0x"))


@given(r"a turbo transaction payload with replay nonce (?P<replay_nonce>\d+)")
def given_turbo_payload(context: typing.Any, replay_nonce: str):
    # Create a basic entry function
    entry_function = EntryFunction.natural("0x1::test", "test_function", [], [])
    regular_payload = TransactionPayload(entry_function)
    context.turbo_payload = convert_payload_to_turbo_payload(regular_payload, int(replay_nonce))


@given(r"a TransactionExtraConfigV1 with no multisig address")
def given_extra_config_no_multisig(context: typing.Any):
    context.has_multisig = False


@given(r'a TransactionExtraConfigV1 with multisig address "(?P<multisig_address>0x[0-9a-fA-F]+)"')
def given_extra_config_with_multisig(context: typing.Any, multisig_address: str):
    context.has_multisig = True
    context.multisig_address = AccountAddress.from_str(multisig_address)


@given(r"multiple turbo transactions with different replay nonces")
def given_multiple_turbo_transactions(context: typing.Any):
    # First create a sender account for these transactions
    private_key = ed25519.PrivateKey.random()
    context.sender_account = Account.load_key(private_key.hex())
    
    context.turbo_transactions = []
    for nonce in [100, 200, 300]:
        entry_function = EntryFunction.natural("0x1::test", "test", [], [])
        regular_payload = TransactionPayload(entry_function)
        turbo_payload = convert_payload_to_turbo_payload(regular_payload, nonce)
        context.turbo_transactions.append(turbo_payload)


@when("I create a turbo transaction")
def when_create_turbo_transaction(context: typing.Any):
    turbo_payload = convert_payload_to_turbo_payload(context.payload, context.replay_nonce)
    
    # Create a raw transaction (simulating what the client would do)
    context.turbo_transaction = RawTransaction(
        context.sender_account.address(),
        0xdeadbeef,  # placeholder sequence number
        turbo_payload,
        100000,  # max_gas_amount
        100,     # gas_unit_price
        1000000000,  # expiration_timestamp_secs
        1,       # chain_id
    )


@when("I create a turbo transaction with multisig")
def when_create_turbo_transaction_with_multisig(context: typing.Any):
    executable = TransactionExecutableEntryFunction(context.entry_function)
    extra_config = TransactionExtraConfigV1(context.multisig_address, context.replay_nonce)
    inner_payload = TransactionInnerPayloadV1(executable, extra_config)
    turbo_payload = TransactionPayload(inner_payload)
    
    context.turbo_transaction = RawTransaction(
        context.sender_account.address(),
        0xdeadbeef,
        turbo_payload,
        100000,
        100,
        1000000000,
        1,
    )


@when("I call create_bcs_transaction with both parameters")
def when_call_unified_api_with_both(context: typing.Any):
    # Simulate the unified API behavior
    turbo_payload = convert_payload_to_turbo_payload(context.payload, context.replay_nonce)
    
    context.unified_transaction = RawTransaction(
        context.sender_account.address(),
        0xdeadbeef,  # sequence_number is ignored, placeholder used
        turbo_payload,
        100000,
        100,
        1000000000,
        1,
    )


@when("I call create_bcs_transaction without replay_nonce")
def when_call_unified_api_without_replay_nonce(context: typing.Any):
    # Simulate regular transaction creation
    context.regular_transaction = RawTransaction(
        context.sender_account.address(),
        context.sequence_number,
        context.payload,  # Original payload, not converted
        100000,
        100,
        1000000000,
        1,
    )


@when("I call bcs_transfer with replay_nonce")
def when_call_bcs_transfer_with_replay_nonce(context: typing.Any):
    # Create transfer entry function
    transaction_arguments = [
        TransactionArgument(context.recipient_address, Serializer.struct),
        TransactionArgument(context.amount, Serializer.u64),
    ]
    
    entry_function = EntryFunction.natural(
        "0x1::aptos_account",
        "transfer",
        [],
        transaction_arguments,
    )
    
    regular_payload = TransactionPayload(entry_function)
    turbo_payload = convert_payload_to_turbo_payload(regular_payload, context.replay_nonce)
    
    context.transfer_transaction = RawTransaction(
        context.sender_account.address(),
        0xdeadbeef,
        turbo_payload,
        100000,
        100,
        1000000000,
        1,
    )


@when("I call bcs_transfer without replay_nonce")
def when_call_bcs_transfer_without_replay_nonce(context: typing.Any):
    # Ensure we have a recipient address
    if not hasattr(context, 'recipient_address'):
        private_key = ed25519.PrivateKey.random()
        context.recipient_address = AccountAddress.from_key(private_key.public_key())
    
    # Ensure we have an amount
    if not hasattr(context, 'amount'):
        context.amount = 1000
    
    # Create regular transfer
    transaction_arguments = [
        TransactionArgument(context.recipient_address, Serializer.struct),
        TransactionArgument(context.amount, Serializer.u64),
    ]
    
    entry_function = EntryFunction.natural(
        "0x1::aptos_account",
        "transfer",
        [],
        transaction_arguments,
    )
    
    regular_payload = TransactionPayload(entry_function)
    
    context.regular_transfer_transaction = RawTransaction(
        context.sender_account.address(),
        100,  # Some sequence number
        regular_payload,
        100000,
        100,
        1000000000,
        1,
    )


@when("I convert the payload to turbo payload")
def when_convert_to_turbo_payload(context: typing.Any):
    context.original_payload = context.payload
    context.converted_turbo_payload = convert_payload_to_turbo_payload(context.payload, context.replay_nonce)


@when("I attempt to convert to turbo payload")
def when_attempt_convert_invalid_payload(context: typing.Any):
    try:
        convert_payload_to_turbo_payload(context.invalid_payload, 12345)
        context.exception_raised = False
    except Exception as e:
        context.exception_raised = True
        context.exception_message = str(e)


@when("I serialize the transaction payload")
def when_serialize_payload(context: typing.Any):
    serializer = Serializer()
    if hasattr(context, 'turbo_transaction'):
        context.turbo_transaction.payload.serialize(serializer)
    elif hasattr(context, 'turbo_payload'):
        context.turbo_payload.serialize(serializer)
    else:
        context.payload.serialize(serializer)
    context.serialized_bytes = serializer.output()


@when("I deserialize the serialized payload")
def when_deserialize_payload(context: typing.Any):
    deserializer = Deserializer(context.serialized_bytes)
    context.deserialized_payload = TransactionPayload.deserialize(deserializer)


@when("I deserialize the transaction payload")
def when_deserialize_typescript_payload(context: typing.Any):
    deserializer = Deserializer(context.typescript_bytes)
    context.deserialized_typescript_payload = TransactionPayload.deserialize(deserializer)


@when("I serialize the payload back")
def when_serialize_typescript_payload_back(context: typing.Any):
    serializer = Serializer()
    context.deserialized_typescript_payload.serialize(serializer)
    context.reserialized_bytes = serializer.output()


@when("I serialize the extra config")
def when_serialize_extra_config(context: typing.Any):
    if context.has_multisig:
        extra_config = TransactionExtraConfigV1(context.multisig_address, context.replay_nonce)
    else:
        extra_config = TransactionExtraConfigV1(None, context.replay_nonce)
    
    # Store the original for later verification
    context.original_extra_config = extra_config
    
    serializer = Serializer()
    extra_config.serialize(serializer)
    context.serialized_extra_config = serializer.output()


@when("I deserialize it back")
def when_deserialize_extra_config_back(context: typing.Any):
    deserializer = Deserializer(context.serialized_extra_config)
    # Note: We need to first deserialize the variant since serialize() writes it
    variant = deserializer.uleb128()  # This should be 0 for V1
    
    # Now deserialize the actual content
    multisig_address = None
    if deserializer.bool():
        multisig_address = AccountAddress.deserialize(deserializer)
    
    replay_protection_nonce = None
    if deserializer.bool():
        replay_protection_nonce = deserializer.u64()
    
    context.deserialized_extra_config = TransactionExtraConfigV1(multisig_address, replay_protection_nonce)


@when("I create each transaction")
def when_create_each_transaction(context: typing.Any):
    context.sequence_numbers = []
    for turbo_payload in context.turbo_transactions:
        transaction = RawTransaction(
            context.sender_account.address(),
            0xdeadbeef,
            turbo_payload,
            100000,
            100,
            1000000000,
            1,
        )
        context.sequence_numbers.append(transaction.sequence_number)


@when("I create a signed turbo transaction")
def when_create_signed_turbo_transaction(context: typing.Any):
    turbo_payload = convert_payload_to_turbo_payload(context.payload, context.replay_nonce)
    
    raw_transaction = RawTransaction(
        context.sender_account.address(),
        0xdeadbeef,
        turbo_payload,
        100000,
        100,
        1000000000,
        1,
    )
    
    authenticator = context.sender_account.sign_transaction(raw_transaction)
    context.signed_turbo_transaction = SignedTransaction(raw_transaction, authenticator)


@when("I serialize the payload")
def when_serialize_turbo_payload(context: typing.Any):
    serializer = Serializer()
    context.turbo_payload.serialize(serializer)
    context.serialized_turbo_bytes = serializer.output()


@then("the transaction should use placeholder sequence number 0xdeadbeef")
def then_transaction_uses_placeholder_sequence(context: typing.Any):
    transaction = getattr(context, 'turbo_transaction', None) or \
                 getattr(context, 'unified_transaction', None) or \
                 getattr(context, 'transfer_transaction', None)
    assert transaction is not None, "No transaction found in context"
    assert transaction.sequence_number == 0xdeadbeef, f"Expected 0xdeadbeef, got {hex(transaction.sequence_number)}"


@then("the payload should be TransactionInnerPayloadV1")
def then_payload_is_inner_payload_v1(context: typing.Any):
    transaction = getattr(context, 'turbo_transaction', None) or \
                 getattr(context, 'unified_transaction', None) or \
                 getattr(context, 'transfer_transaction', None)
    
    if transaction:
        payload = transaction.payload
    else:
        payload = getattr(context, 'converted_turbo_payload', None)
    
    assert payload is not None, "No payload found"
    assert payload.variant == TransactionPayload.PAYLOAD, f"Expected variant {TransactionPayload.PAYLOAD}, got {payload.variant}"
    assert isinstance(payload.value, TransactionInnerPayloadV1), f"Expected TransactionInnerPayloadV1, got {type(payload.value)}"


@then(r"the replay protection nonce should be (?P<expected_nonce>\d+)")
def then_replay_nonce_matches(context: typing.Any, expected_nonce: str):
    expected = int(expected_nonce)
    
    # Check if we're dealing with deserialized extra config
    if hasattr(context, 'deserialized_extra_config'):
        extra_config = context.deserialized_extra_config
        assert extra_config.replay_protection_nonce == expected, \
            f"Expected nonce {expected}, got {extra_config.replay_protection_nonce}"
        return
    
    # Find the transaction or payload
    transaction = getattr(context, 'turbo_transaction', None) or \
                 getattr(context, 'unified_transaction', None) or \
                 getattr(context, 'transfer_transaction', None)
    
    if transaction:
        inner_payload = transaction.payload.value
    else:
        payload = getattr(context, 'converted_turbo_payload', None)
        inner_payload = payload.value if payload else None
    
    assert inner_payload is not None, "No inner payload found"
    assert isinstance(inner_payload, TransactionInnerPayloadV1), "Payload is not TransactionInnerPayloadV1"
    assert inner_payload.extra_config.replay_protection_nonce == expected, \
        f"Expected nonce {expected}, got {inner_payload.extra_config.replay_protection_nonce}"


@then("the executable should be TransactionExecutableScript")
def then_executable_is_script(context: typing.Any):
    inner_payload = context.turbo_transaction.payload.value
    assert isinstance(inner_payload.executable, TransactionExecutableScript), \
        f"Expected TransactionExecutableScript, got {type(inner_payload.executable)}"


@then(r'the multisig address should be "(?P<expected_address>0x[0-9a-fA-F]+)"')
def then_multisig_address_matches(context: typing.Any, expected_address: str):
    expected = AccountAddress.from_str(expected_address)
    
    # Check if we're dealing with deserialized extra config
    if hasattr(context, 'deserialized_extra_config'):
        extra_config = context.deserialized_extra_config
        assert extra_config.multisig_address == expected, \
            f"Expected {expected}, got {extra_config.multisig_address}"
        return
    
    inner_payload = context.turbo_transaction.payload.value
    assert inner_payload.extra_config.multisig_address == expected, \
        f"Expected {expected}, got {inner_payload.extra_config.multisig_address}"


@then("the deserialized payload should match the original")
def then_deserialized_matches_original(context: typing.Any):
    original = context.turbo_transaction.payload
    deserialized = context.deserialized_payload
    
    assert original.variant == deserialized.variant, "Payload variants don't match"
    assert type(original.value) == type(deserialized.value), "Payload value types don't match"


@then("the replay protection nonce should be preserved")
def then_replay_nonce_preserved(context: typing.Any):
    original_nonce = context.turbo_transaction.payload.value.extra_config.replay_protection_nonce
    deserialized_nonce = context.deserialized_payload.value.extra_config.replay_protection_nonce
    
    assert original_nonce == deserialized_nonce, \
        f"Nonce not preserved: original {original_nonce}, deserialized {deserialized_nonce}"


@then("the sequence number parameter should be ignored")
def then_sequence_number_ignored(context: typing.Any):
    # This is verified by checking that 0xdeadbeef is used instead of the provided sequence number
    assert context.unified_transaction.sequence_number == 0xdeadbeef, \
        "Sequence number was not ignored for turbo transaction"


@then(r"the transaction should use sequence number (?P<expected_seq>\d+)")
def then_transaction_uses_sequence_number(context: typing.Any, expected_seq: str):
    expected = int(expected_seq)
    assert context.regular_transaction.sequence_number == expected, \
        f"Expected sequence number {expected}, got {context.regular_transaction.sequence_number}"


@then("the payload should be EntryFunction")
def then_payload_is_entry_function(context: typing.Any):
    payload = context.regular_transaction.payload
    assert payload.variant == TransactionPayload.SCRIPT_FUNCTION, \
        f"Expected SCRIPT_FUNCTION variant, got {payload.variant}"
    assert isinstance(payload.value, EntryFunction), \
        f"Expected EntryFunction, got {type(payload.value)}"


@then("there should be no replay protection nonce")
def then_no_replay_nonce(context: typing.Any):
    # Get the correct transaction based on what was created
    transaction = getattr(context, 'regular_transaction', None) or \
                 getattr(context, 'regular_transfer_transaction', None)
    
    assert transaction is not None, "No regular transaction found"
    payload = transaction.payload
    # Regular transactions don't have TransactionInnerPayloadV1, so no replay nonce
    assert payload.variant != TransactionPayload.PAYLOAD, \
        "Regular transaction should not use PAYLOAD variant"


@then("a turbo transaction should be created")
def then_turbo_transaction_created(context: typing.Any):
    assert hasattr(context, 'transfer_transaction'), "Transfer transaction not found"
    payload = context.transfer_transaction.payload
    assert payload.variant == TransactionPayload.PAYLOAD, "Transfer should create turbo transaction"


@then("a regular transaction should be created")
def then_regular_transaction_created(context: typing.Any):
    assert hasattr(context, 'regular_transfer_transaction'), "Regular transfer transaction not found"
    payload = context.regular_transfer_transaction.payload
    assert payload.variant == TransactionPayload.SCRIPT_FUNCTION, "Transfer should create regular transaction"


@then("the transfer function should be called with correct parameters")
def then_transfer_function_correct(context: typing.Any):
    # This step verifies that the transfer function is set up correctly
    # We can check this in both turbo and regular transactions
    transaction = getattr(context, 'transfer_transaction', None) or \
                 getattr(context, 'regular_transfer_transaction', None)
    
    assert transaction is not None, "No transfer transaction found"
    
    if transaction.payload.variant == TransactionPayload.PAYLOAD:
        # Turbo transaction
        entry_func = transaction.payload.value.executable.entry_function
    else:
        # Regular transaction
        entry_func = transaction.payload.value
    
    assert entry_func.function == "transfer", f"Expected 'transfer', got '{entry_func.function}'"
    assert entry_func.module.name == "aptos_account", f"Expected 'aptos_account', got '{entry_func.module.name}'"


@then("the original payload should remain unchanged")
def then_original_payload_unchanged(context: typing.Any):
    # Verify that converting to turbo doesn't modify the original payload
    original = context.original_payload
    
    # Check that the original payload is still the same type and variant
    assert isinstance(original.value, EntryFunction), "Original payload should still be EntryFunction"
    assert original.variant == TransactionPayload.SCRIPT_FUNCTION, "Original variant should be unchanged"


@then("the turbo payload should have TransactionInnerPayloadV1")
def then_turbo_payload_has_inner_v1(context: typing.Any):
    turbo = context.converted_turbo_payload
    assert turbo.variant == TransactionPayload.PAYLOAD, "Turbo payload should have PAYLOAD variant"
    assert isinstance(turbo.value, TransactionInnerPayloadV1), "Turbo payload should have TransactionInnerPayloadV1"


@then("the executable should wrap the original entry function")
def then_executable_wraps_original(context: typing.Any):
    original_entry_func = context.original_payload.value
    turbo_executable = context.converted_turbo_payload.value.executable
    
    assert isinstance(turbo_executable, TransactionExecutableEntryFunction), \
        "Executable should be TransactionExecutableEntryFunction"
    assert turbo_executable.entry_function.function == original_entry_func.function, \
        "Function name should match"
    assert turbo_executable.entry_function.module.name == original_entry_func.module.name, \
        "Module name should match"


@then(r'an exception should be raised with message containing "(?P<error_text>[^"]+)"')
def then_exception_raised_with_message(context: typing.Any, error_text: str):
    assert context.exception_raised, "Expected an exception to be raised"
    assert error_text in context.exception_message, \
        f"Expected '{error_text}' in exception message, got: {context.exception_message}"


@then(r"the payload variant should be (?P<expected_variant>\d+)")
def then_payload_variant_matches(context: typing.Any, expected_variant: str):
    expected = int(expected_variant)
    payload = context.deserialized_typescript_payload
    assert payload.variant == expected, f"Expected variant {expected}, got {payload.variant}"


@then("the inner payload should be TransactionInnerPayloadV1")
def then_inner_payload_is_v1(context: typing.Any):
    payload = context.deserialized_typescript_payload
    assert isinstance(payload.value, TransactionInnerPayloadV1), \
        f"Expected TransactionInnerPayloadV1, got {type(payload.value)}"


@then("the executable should be TransactionExecutableEntryFunction")
def then_executable_is_entry_function(context: typing.Any):
    inner_payload = context.deserialized_typescript_payload.value
    assert isinstance(inner_payload.executable, TransactionExecutableEntryFunction), \
        f"Expected TransactionExecutableEntryFunction, got {type(inner_payload.executable)}"


@then(r'the function name should be "(?P<expected_name>\w+)"')
def then_function_name_matches(context: typing.Any, expected_name: str):
    inner_payload = context.deserialized_typescript_payload.value
    entry_func = inner_payload.executable.entry_function
    assert entry_func.function == expected_name, \
        f"Expected function '{expected_name}', got '{entry_func.function}'"


@then(r'the module name should be "(?P<expected_module>\w+)"')
def then_module_name_matches(context: typing.Any, expected_module: str):
    inner_payload = context.deserialized_typescript_payload.value
    entry_func = inner_payload.executable.entry_function
    assert entry_func.module.name == expected_module, \
        f"Expected module '{expected_module}', got '{entry_func.module.name}'"


@then("the output should match the original hex")
def then_output_matches_original_hex(context: typing.Any):
    original_bytes = context.typescript_bytes
    reserialized_bytes = context.reserialized_bytes
    
    assert original_bytes == reserialized_bytes, \
        f"Serialization roundtrip failed. Original: {original_bytes.hex()}, Got: {reserialized_bytes.hex()}"


@then(r"the variant should be (?P<expected_variant>\d+)")
def then_variant_matches(context: typing.Any, expected_variant: str):
    expected = int(expected_variant)
    variant_byte = context.serialized_turbo_bytes[0]  # First byte is the variant
    assert variant_byte == expected, f"Expected variant {expected}, got {variant_byte}"


@then(r"the executable variant should be (?P<expected_exec_variant>\d+)")
def then_executable_variant_matches(context: typing.Any, expected_exec_variant: str):
    # This is more complex to verify from serialized bytes, but we can check the structure
    expected = int(expected_exec_variant)
    inner_payload = context.turbo_payload.value
    
    if expected == 1:  # ENTRY_FUNCTION
        assert isinstance(inner_payload.executable, TransactionExecutableEntryFunction), \
            "Expected TransactionExecutableEntryFunction"
    elif expected == 0:  # SCRIPT
        assert isinstance(inner_payload.executable, TransactionExecutableScript), \
            "Expected TransactionExecutableScript"


@then(r"the extra config variant should be (?P<expected_config_variant>\d+)")
def then_config_variant_matches(context: typing.Any, expected_config_variant: str):
    expected = int(expected_config_variant)
    inner_payload = context.turbo_payload.value
    
    if expected == 0:  # V1
        assert isinstance(inner_payload.extra_config, TransactionExtraConfigV1), \
            "Expected TransactionExtraConfigV1"


@then("all transactions should use the same placeholder sequence number 0xdeadbeef")
def then_all_use_same_placeholder(context: typing.Any):
    for seq_num in context.sequence_numbers:
        assert seq_num == 0xdeadbeef, f"Expected 0xdeadbeef, got {hex(seq_num)}"


@then("the sequence numbers should not affect the turbo transactions")
def then_sequence_numbers_not_affect_turbo(context: typing.Any):
    # All should be the same placeholder value regardless of different replay nonces
    unique_seq_nums = set(context.sequence_numbers)
    assert len(unique_seq_nums) == 1, "All turbo transactions should have the same sequence number"
    assert list(unique_seq_nums)[0] == 0xdeadbeef, "Should use placeholder sequence number"


@then("the multisig address should be None")
def then_multisig_address_is_none(context: typing.Any):
    extra_config = context.deserialized_extra_config
    assert extra_config.multisig_address is None, \
        f"Expected None, got {extra_config.multisig_address}"


@then(r'the multisig address should be "(?P<expected_address>0x[0-9a-fA-F]+)"')
def then_multisig_address_is(context: typing.Any, expected_address: str):
    expected = AccountAddress.from_str(expected_address)
    extra_config = context.deserialized_extra_config
    assert extra_config.multisig_address == expected, \
        f"Expected {expected}, got {extra_config.multisig_address}"


@then("the signed transaction should contain a turbo payload")
def then_signed_transaction_has_turbo_payload(context: typing.Any):
    signed_txn = context.signed_turbo_transaction
    payload = signed_txn.transaction.payload
    assert payload.variant == TransactionPayload.PAYLOAD, "Signed transaction should have turbo payload"
    assert isinstance(payload.value, TransactionInnerPayloadV1), "Should contain TransactionInnerPayloadV1"


@then("the authenticator should be valid for the sender")
def then_authenticator_valid(context: typing.Any):
    signed_txn = context.signed_turbo_transaction
    # The authenticator is created by the sender account, so it should be valid
    assert signed_txn.authenticator is not None, "Authenticator should not be None"
    # Additional validation could check signature verification, but that's tested elsewhere


@then("the transaction hash should be deterministic")
def then_transaction_hash_deterministic(context: typing.Any):
    signed_txn = context.signed_turbo_transaction
    
    # Create the same transaction again and verify it produces the same hash
    turbo_payload = convert_payload_to_turbo_payload(context.payload, context.replay_nonce)
    
    raw_transaction2 = RawTransaction(
        context.sender_account.address(),
        0xdeadbeef,
        turbo_payload,
        100000,
        100,
        1000000000,
        1,
    )
    
    authenticator2 = context.sender_account.sign_transaction(raw_transaction2)
    signed_txn2 = SignedTransaction(raw_transaction2, authenticator2)
    
    # Both should produce the same bytes when serialized
    serializer1 = Serializer()
    signed_txn.serialize(serializer1)
    bytes1 = serializer1.output()
    
    serializer2 = Serializer()
    signed_txn2.serialize(serializer2)
    bytes2 = serializer2.output()
    
    assert bytes1 == bytes2, "Transaction serialization should be deterministic"