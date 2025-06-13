Feature: Turbo (Orderless) Transactions
"""
AIP-123 Support for turbo transactions, where a user can submit
transactions with a unique replay nonce rather than a sequential sequence
number, enabling orderless execution.
"""

  Scenario Outline: Create turbo transaction with replay nonce
    Given a sender account
    And an entry function payload for "<function_name>"
    And a replay nonce <replay_nonce>
    When I create a turbo transaction
    Then the transaction should use placeholder sequence number 0xdeadbeef
    And the payload should be TransactionInnerPayloadV1
    And the replay protection nonce should be <replay_nonce>

    Examples:
      | function_name | replay_nonce |
      | transfer      | 12345        |
      | transfer      | 98765        |
      | transfer      | 1            |

  Scenario Outline: Create turbo transaction with script payload
    Given a sender account
    And a script payload with code <script_code>
    And a replay nonce <replay_nonce>
    When I create a turbo transaction
    Then the transaction should use placeholder sequence number 0xdeadbeef
    And the payload should be TransactionInnerPayloadV1
    And the executable should be TransactionExecutableScript
    And the replay protection nonce should be <replay_nonce>

    Examples:
      | script_code      | replay_nonce |
      | "0x00010203"     | 54321        |
      | "0xdeadbeef"     | 11111        |

  Scenario: Create turbo transaction with multisig address
    Given a sender account
    And an entry function payload for "transfer"
    And a multisig address "0x0000000000000000000000000000000000000000000000000000000000000123"
    And a replay nonce 99999
    When I create a turbo transaction with multisig
    Then the transaction should use placeholder sequence number 0xdeadbeef
    And the payload should be TransactionInnerPayloadV1
    And the multisig address should be "0x0000000000000000000000000000000000000000000000000000000000000123"
    And the replay protection nonce should be 99999

  Scenario: Turbo transaction serialization roundtrip
    Given a sender account
    And an entry function payload for "transfer"
    And a replay nonce 12345
    When I create a turbo transaction
    And I serialize the transaction payload
    And I deserialize the serialized payload
    Then the deserialized payload should match the original
    And the replay protection nonce should be preserved

  Scenario Outline: Unified API creates turbo transaction when replay_nonce provided
    Given a sender account
    And an entry function payload for "transfer"
    And a sequence number <sequence_number>
    And a replay nonce <replay_nonce>
    When I call create_bcs_transaction with both parameters
    Then the transaction should use placeholder sequence number 0xdeadbeef
    And the sequence number parameter should be ignored
    And the payload should be TransactionInnerPayloadV1
    And the replay protection nonce should be <replay_nonce>

    Examples:
      | sequence_number | replay_nonce |
      | 10              | 12345        |
      | 999             | 54321        |

  Scenario: Unified API creates regular transaction when replay_nonce not provided
    Given a sender account
    And an entry function payload for "transfer"
    And a sequence number 42
    When I call create_bcs_transaction without replay_nonce
    Then the transaction should use sequence number 42
    And the payload should be EntryFunction
    And there should be no replay protection nonce

  Scenario Outline: BCS transfer with turbo transaction
    Given a sender account
    And a recipient address
    And an amount <amount>
    And a replay nonce <replay_nonce>
    When I call bcs_transfer with replay_nonce
    Then a turbo transaction should be created
    And the transfer function should be called with correct parameters
    And the replay protection nonce should be <replay_nonce>

    Examples:
      | amount | replay_nonce |
      | 1000   | 12345        |
      | 5000   | 98765        |

  Scenario: BCS transfer with regular transaction (backward compatibility)
    Given a sender account
    When I call bcs_transfer without replay_nonce
    Then a regular transaction should be created
    And the transfer function should be called with correct parameters
    And there should be no replay protection nonce

  Scenario Outline: TransactionInnerPayload serialization compatibility
    Given a turbo transaction payload with replay nonce <replay_nonce>
    When I serialize the payload
    Then the variant should be <expected_variant>
    And the executable variant should be <executable_variant>
    And the extra config variant should be <config_variant>

    Examples:
      | replay_nonce | expected_variant | executable_variant | config_variant |
      | 12345        | 4                | 1                  | 0              |
      | 0            | 4                | 1                  | 0              |

  Scenario: Convert regular payload to turbo payload
    Given an entry function payload for "transfer"
    And a replay nonce 12345
    When I convert the payload to turbo payload
    Then the original payload should remain unchanged
    And the turbo payload should have TransactionInnerPayloadV1
    And the executable should wrap the original entry function
    And the replay protection nonce should be 12345

  Scenario Outline: Invalid turbo transaction creation
    Given a sender account
    And an invalid payload type <payload_type>
    And a replay nonce 12345
    When I attempt to convert to turbo payload
    Then an exception should be raised with message containing "<error_message>"

    Examples:
      | payload_type   | error_message                    |
      | MODULE_BUNDLE  | Unsupported payload type         |
      | MULTISIG       | Unsupported payload type         |

  Scenario: Turbo transaction hex deserialization and serialization
    Given a turbo transaction hex payload "0x04000100000000000000000000000000000000000000000000000000000000000000010d6170746f735f6163636f756e74087472616e73666572000220bd3c821fc733b9e0a022c7fa2fe24e5a5a0c5b66c9624d5a63ea735628818f1008e8030000000000000000010001000000000000"
    When I deserialize the transaction payload
    Then the payload variant should be 4
    And the inner payload should be TransactionInnerPayloadV1
    And the executable should be TransactionExecutableEntryFunction
    And the function name should be "transfer"
    And the module name should be "aptos_account"
    When I serialize the payload back
    Then the output should match the original hex

  Scenario: Placeholder sequence number consistency
    Given multiple turbo transactions with different replay nonces
    When I create each transaction
    Then all transactions should use the same placeholder sequence number 0xdeadbeef
    And the sequence numbers should not affect the turbo transactions

  Scenario: Extra config serialization with optional fields
    Given a TransactionExtraConfigV1 with no multisig address
    And a replay protection nonce 12345
    When I serialize the extra config
    And I deserialize it back
    Then the multisig address should be None
    And the replay protection nonce should be 12345

  Scenario: Extra config serialization with multisig address
    Given a TransactionExtraConfigV1 with multisig address "0x0000000000000000000000000000000000000000000000000000000000000456"
    And a replay protection nonce 67890
    When I serialize the extra config
    And I deserialize it back
    Then the multisig address should be "0x0000000000000000000000000000000000000000000000000000000000000456"
    And the replay protection nonce should be 67890

  Scenario: Signed turbo transaction creation
    Given a sender account
    And an entry function payload for "transfer"
    And a replay nonce 12345
    When I create a signed turbo transaction
    Then the signed transaction should contain a turbo payload
    And the authenticator should be valid for the sender
    And the transaction hash should be deterministic