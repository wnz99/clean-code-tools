const DEFAULT_TODO_PATTERN = "^(TODO|FIXME|XXX)\\([A-Z][A-Z0-9]+-\\d+\\):\\s+\\S";
const DEFAULT_SELECTOR_PARAM_NAMES = [
  "flag",
  "mode",
  "option",
  "type",
  "kind",
  "variant",
  "selector",
  "enabled",
  "disabled",
  "dryRun",
  "verbose",
  "silent",
  "force",
  "skip",
  "include",
  "exclude",
];
const DEFAULT_MUTATOR_METHODS = [
  "add",
  "append",
  "clear",
  "copyWithin",
  "delete",
  "fill",
  "pop",
  "push",
  "reverse",
  "set",
  "shift",
  "sort",
  "splice",
  "unshift",
];
const DEFAULT_LITERAL_CALL_ALLOWLIST = [
  "BigInt",
  "Boolean",
  "Date",
  "Error",
  "Number",
  "RegExp",
  "String",
  "Symbol",
  "console.debug",
  "console.error",
  "console.info",
  "console.log",
  "console.warn",
  "expect",
  "it",
  "test",
];

function createRule({ name, meta, create }) {
  return {
    meta: {
      docs: {
        url: `https://github.com/local/clean-code-tools/blob/main/docs/eslint-custom-rules.md#clean-code${name}`,
        ...meta.docs,
      },
      ...meta,
    },
    create,
  };
}

function getSourceCode(context) {
  return context.sourceCode ?? context.getSourceCode();
}

function cleanCommentText(comment) {
  return comment.value.trim().replace(/^\*+\s?/gm, "").trim();
}

function normalizeWords(value) {
  return value
    .replace(/[_$]+/gu, " ")
    .replace(/([a-z])([A-Z])/gu, "$1 $2")
    .toLowerCase()
    .match(/[a-z][a-z0-9]+/gu) ?? [];
}

function getIdentifierName(node) {
  if (!node) {
    return undefined;
  }
  if (node.type === "Identifier") {
    return node.name;
  }
  if (node.type === "PrivateIdentifier") {
    return node.name;
  }
  if (node.type === "ThisExpression") {
    return "this";
  }
  if (node.type === "MemberExpression" || node.type === "OptionalMemberExpression") {
    return getIdentifierName(node.property);
  }
  return undefined;
}

function getCalleeName(callee) {
  if (!callee) {
    return undefined;
  }
  if (callee.type === "Identifier") {
    return callee.name;
  }
  if (callee.type === "MemberExpression" || callee.type === "OptionalMemberExpression") {
    const objectName = getCalleeName(callee.object);
    const propertyName = getIdentifierName(callee.property);
    return objectName && propertyName ? `${objectName}.${propertyName}` : propertyName;
  }
  return undefined;
}

function unwrapExpression(node) {
  let current = node;
  while (
    current &&
    ["ChainExpression", "TSAsExpression", "TSTypeAssertion", "TSNonNullExpression"].includes(current.type)
  ) {
    current = current.expression;
  }
  return current;
}

function isBooleanLiteral(node) {
  const unwrapped = unwrapExpression(node);
  return unwrapped?.type === "Literal" && typeof unwrapped.value === "boolean";
}

function isStringOrNumberLiteral(node) {
  const unwrapped = unwrapExpression(node);
  return (
    unwrapped?.type === "Literal" &&
    (typeof unwrapped.value === "string" || typeof unwrapped.value === "number")
  );
}

function collectPatternIdentifiers(node) {
  const identifiers = [];

  function collect(current) {
    if (!current) {
      return;
    }
    switch (current.type) {
      case "Identifier":
        identifiers.push(current.name);
        break;
      case "AssignmentPattern":
        collect(current.left);
        break;
      case "ArrayPattern":
        for (const element of current.elements) {
          collect(element);
        }
        break;
      case "ObjectPattern":
        for (const property of current.properties) {
          collect(property.value ?? property.argument);
        }
        break;
      case "RestElement":
        collect(current.argument);
        break;
    }
  }

  collect(node);
  return identifiers;
}

function getRootIdentifierName(node) {
  const unwrapped = unwrapExpression(node);
  if (!unwrapped) {
    return undefined;
  }
  if (unwrapped.type === "Identifier") {
    return unwrapped.name;
  }
  if (unwrapped.type === "MemberExpression" || unwrapped.type === "OptionalMemberExpression") {
    return getRootIdentifierName(unwrapped.object);
  }
  return undefined;
}

function firstLineAfterComment(sourceCode, comment) {
  const line = comment.loc.end.line + 1;
  const lines = sourceCode.lines ?? sourceCode.getText().split(/\r?\n/u);
  return lines[line - 1]?.trim() ?? "";
}

function isLikelyCodeComment(text) {
  const trimmed = text.trim();
  if (trimmed.length < 4) {
    return false;
  }
  const codePatterns = [
    /\b(await|const|let|var|function|class|interface|type|enum|return|throw|if|for|while|switch|import|export)\b/u,
    /(?:^|\s)[\w$.]+\s*\([^)]*\)\s*;?$/u,
    /=>/u,
    /[{}]/u,
    /^\s*<\/?[A-Za-z][^>]*>\s*$/u,
  ];
  return codePatterns.some((pattern) => pattern.test(trimmed));
}

function isSeparatorComment(text) {
  const compact = text.replace(/\s+/gu, "");
  return compact.length >= 8 && /^[-=*_/#]+$/u.test(compact);
}

function isBylineComment(text) {
  return /\b(author|created by|written by|modified by|last modified|since)\b/iu.test(text);
}

function isDateOnlyComment(text) {
  return /\b(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b/u.test(text);
}

function isClosingBraceComment(sourceCode, comment) {
  const text = sourceCode.getText();
  const lineStart = text.lastIndexOf("\n", comment.range[0] - 1) + 1;
  const before = text.slice(lineStart, comment.range[0]);
  return /\}\s*$/u.test(before);
}

function literalLooksLikePolicy(value) {
  if (typeof value === "number") {
    return ![-1, 0, 1].includes(value);
  }
  if (typeof value !== "string") {
    return false;
  }
  if (value.length < 2) {
    return false;
  }
  return (
    /^[A-Z][A-Z0-9_]+$/u.test(value) ||
    /^\d{4}-\d{2}-\d{2}$/u.test(value) ||
    /(?:^|[_\s-])(active|approved|cancelled|canceled|draft|failed|paid|pending|rejected|retry|suspended)(?:$|[_\s-])/iu.test(
      value,
    )
  );
}

function isAllowedLiteralContext(node, callAllowlist) {
  let current = node.parent;
  while (current) {
    if (current.type === "ImportDeclaration" || current.type === "ExportNamedDeclaration") {
      return true;
    }
    if (current.type === "Property" && current.key === node) {
      return true;
    }
    if (current.type === "VariableDeclarator" && current.id?.type === "Identifier" && /^[A-Z][A-Z0-9_]+$/u.test(current.id.name)) {
      return true;
    }
    if (current.type === "CallExpression" || current.type === "NewExpression") {
      const calleeName = getCalleeName(current.callee);
      return callAllowlist.includes(calleeName);
    }
    current = current.parent;
  }
  return false;
}

function isTypeOnlyLiteral(node) {
  let current = node.parent;
  while (current) {
    if (
      current.type === "TSLiteralType" ||
      current.type === "TSTypeAliasDeclaration" ||
      current.type === "TSInterfaceDeclaration" ||
      current.type === "TSEnumDeclaration" ||
      current.type === "TSTypeAnnotation" ||
      current.type === "TSTypeReference" ||
      current.type === "TSUnionType" ||
      current.type === "TSIntersectionType"
    ) {
      return true;
    }
    current = current.parent;
  }
  return false;
}

function isBooleanTypeAnnotation(node) {
  const annotation = node?.typeAnnotation;
  return annotation?.type === "TSBooleanKeyword" || annotation?.typeAnnotation?.type === "TSBooleanKeyword";
}

function nameLooksLikeSelector(name, configuredNames) {
  const lowerName = name.toLowerCase();
  return configuredNames.some((configuredName) => lowerName.includes(configuredName.toLowerCase()));
}

function isMemberDepthTooDeep(node, maxDepth) {
  let depth = 0;
  let current = unwrapExpression(node);
  while (current?.type === "MemberExpression" || current?.type === "OptionalMemberExpression") {
    depth += 1;
    current = unwrapExpression(current.object);
  }
  return depth > maxDepth;
}

const todoFormat = createRule({
  name: "/todo-format",
  meta: {
    type: "suggestion",
    docs: {
      description: "Require TODO, FIXME, and XXX comments to include an owner or issue identifier.",
    },
    schema: [
      {
        type: "object",
        additionalProperties: false,
        properties: {
          pattern: { type: "string" },
        },
      },
    ],
    messages: {
      invalidTodo:
        "TODO/FIXME comments should include an owner or issue ID, for example TODO(PROJ-123): remove fallback.",
    },
  },
  create(context) {
    const [{ pattern = DEFAULT_TODO_PATTERN } = {}] = context.options;
    const todoPattern = new RegExp(pattern, "iu");
    const sourceCode = getSourceCode(context);

    return {
      Program() {
        for (const comment of sourceCode.getAllComments()) {
          const text = cleanCommentText(comment);
          const todoSegments = text.match(/\b(?:TODO|FIXME|XXX)\b[^\n;]*/giu) ?? [];
          if (todoSegments.some((segment) => !todoPattern.test(segment.trim()))) {
            context.report({ loc: comment.loc, messageId: "invalidTodo" });
          }
        }
      },
    };
  },
});

const noCommentedOutCode = createRule({
  name: "/no-commented-out-code",
  meta: {
    type: "suggestion",
    docs: {
      description: "Flag comments that look like disabled TypeScript or JavaScript code.",
    },
    schema: [],
    messages: {
      commentedOutCode: "Remove commented-out code; version history should preserve old implementations.",
    },
  },
  create(context) {
    const sourceCode = getSourceCode(context);
    return {
      Program() {
        for (const comment of sourceCode.getAllComments()) {
          const text = cleanCommentText(comment);
          if (/\b(?:TODO|FIXME|XXX)\b/iu.test(text)) {
            continue;
          }
          if (isLikelyCodeComment(text)) {
            context.report({ loc: comment.loc, messageId: "commentedOutCode" });
          }
        }
      },
    };
  },
});

const noBooleanFlagArguments = createRule({
  name: "/no-boolean-flag-arguments",
  meta: {
    type: "suggestion",
    docs: {
      description: "Discourage boolean selector arguments and boolean mode parameters.",
    },
    schema: [
      {
        type: "object",
        additionalProperties: false,
        properties: {
          selectorParameterNames: {
            type: "array",
            items: { type: "string" },
          },
        },
      },
    ],
    messages: {
      booleanCallArgument:
        "Boolean literal arguments hide intent at the call site; prefer a named operation or options object.",
      booleanSelectorParameter:
        "Boolean selector parameter '{{name}}' changes behavior by mode; prefer named operations or an explicit options type.",
    },
  },
  create(context) {
    const [{ selectorParameterNames = DEFAULT_SELECTOR_PARAM_NAMES } = {}] = context.options;

    function checkParams(node) {
      for (const parameter of node.params ?? []) {
        const identifiers = collectPatternIdentifiers(parameter);
        const annotatedNode = parameter.type === "AssignmentPattern" ? parameter.left : parameter;
        for (const name of identifiers) {
          if (isBooleanTypeAnnotation(annotatedNode) && nameLooksLikeSelector(name, selectorParameterNames)) {
            context.report({
              node: annotatedNode,
              messageId: "booleanSelectorParameter",
              data: { name },
            });
          }
        }
      }
    }

    function checkArguments(node) {
      for (const argument of node.arguments ?? []) {
        if (isBooleanLiteral(argument)) {
          context.report({ node: argument, messageId: "booleanCallArgument" });
        }
      }
    }

    return {
      ArrowFunctionExpression: checkParams,
      FunctionDeclaration: checkParams,
      FunctionExpression: checkParams,
      CallExpression: checkArguments,
      NewExpression: checkArguments,
    };
  },
});

const noOutputArgumentMutation = createRule({
  name: "/no-output-argument-mutation",
  meta: {
    type: "suggestion",
    docs: {
      description: "Flag parameter mutation that treats arguments as output containers.",
    },
    schema: [
      {
        type: "object",
        additionalProperties: false,
        properties: {
          mutatorMethods: {
            type: "array",
            items: { type: "string" },
          },
        },
      },
    ],
    messages: {
      outputArgument:
        "Avoid mutating parameter '{{name}}' as an output argument; return a value or create a local copy instead.",
    },
  },
  create(context) {
    const [{ mutatorMethods = DEFAULT_MUTATOR_METHODS } = {}] = context.options;
    const functionStack = [];

    function enterFunction(node) {
      functionStack.push({
        locals: new Set(),
        params: new Set((node.params ?? []).flatMap((parameter) => collectPatternIdentifiers(parameter))),
      });
    }

    function exitFunction() {
      functionStack.pop();
    }

    function reportIfParamMutation(node, expression) {
      const name = getRootIdentifierName(expression);
      if (!name) {
        return;
      }
      for (let index = functionStack.length - 1; index >= 0; index -= 1) {
        const scope = functionStack[index];
        if (scope.params.has(name)) {
          context.report({ node, messageId: "outputArgument", data: { name } });
          return;
        }
        if (scope.locals.has(name)) {
          return;
        }
      }
    }

    return {
      ArrowFunctionExpression: enterFunction,
      "ArrowFunctionExpression:exit": exitFunction,
      FunctionDeclaration: enterFunction,
      "FunctionDeclaration:exit": exitFunction,
      FunctionExpression: enterFunction,
      "FunctionExpression:exit": exitFunction,
      VariableDeclarator(node) {
        const scope = functionStack.at(-1);
        if (!scope) {
          return;
        }
        for (const name of collectPatternIdentifiers(node.id)) {
          scope.locals.add(name);
        }
      },
      AssignmentExpression(node) {
        reportIfParamMutation(node.left, node.left);
      },
      UpdateExpression(node) {
        reportIfParamMutation(node.argument, node.argument);
      },
      CallExpression(node) {
        const callee = unwrapExpression(node.callee);
        if (callee?.type !== "MemberExpression" && callee?.type !== "OptionalMemberExpression") {
          return;
        }
        const methodName = getIdentifierName(callee.property);
        if (methodName && mutatorMethods.includes(methodName)) {
          reportIfParamMutation(callee.object, callee.object);
        }
      },
    };
  },
});

const noRedundantComment = createRule({
  name: "/no-redundant-comment",
  meta: {
    type: "suggestion",
    docs: {
      description: "Flag comments that mostly repeat the following line of code.",
    },
    schema: [
      {
        type: "object",
        additionalProperties: false,
        properties: {
          minSharedWords: { type: "integer", minimum: 1 },
          minOverlapRatio: { type: "number", minimum: 0, maximum: 1 },
        },
      },
    ],
    messages: {
      redundantComment: "Comment mostly repeats the next line; prefer making the code name carry the intent.",
    },
  },
  create(context) {
    const [{ minSharedWords = 2, minOverlapRatio = 0.65 } = {}] = context.options;
    const sourceCode = getSourceCode(context);

    return {
      Program() {
        for (const comment of sourceCode.getAllComments()) {
          const commentWords = normalizeWords(cleanCommentText(comment));
          if (commentWords.length < minSharedWords) {
            continue;
          }
          const nextLineWords = normalizeWords(firstLineAfterComment(sourceCode, comment));
          const nextLineWordSet = new Set(nextLineWords);
          const sharedWords = commentWords.filter((word) => nextLineWordSet.has(word));
          if (sharedWords.length >= minSharedWords && sharedWords.length / commentWords.length >= minOverlapRatio) {
            context.report({ loc: comment.loc, messageId: "redundantComment" });
          }
        }
      },
    };
  },
});

const noNoisyComments = createRule({
  name: "/no-noisy-comments",
  meta: {
    type: "suggestion",
    docs: {
      description: "Flag separator, byline/date, and closing-brace comments.",
    },
    schema: [],
    messages: {
      separator: "Separator comments add visual noise; use file structure or named functions instead.",
      byline: "Avoid author/date byline comments in source; version control already records authorship.",
      closingBrace: "Avoid closing-brace comments; extract or shorten the block instead.",
    },
  },
  create(context) {
    const sourceCode = getSourceCode(context);
    return {
      Program() {
        for (const comment of sourceCode.getAllComments()) {
          const text = cleanCommentText(comment);
          if (isSeparatorComment(text)) {
            context.report({ loc: comment.loc, messageId: "separator" });
          } else if (isBylineComment(text) || isDateOnlyComment(text)) {
            context.report({ loc: comment.loc, messageId: "byline" });
          } else if (isClosingBraceComment(sourceCode, comment)) {
            context.report({ loc: comment.loc, messageId: "closingBrace" });
          }
        }
      },
    };
  },
});

const noBusinessPolicyLiterals = createRule({
  name: "/no-business-policy-literals",
  meta: {
    type: "suggestion",
    docs: {
      description: "Flag hard-coded policy literals in branch, return, and call expressions.",
    },
    schema: [
      {
        type: "object",
        additionalProperties: false,
        properties: {
          allowedCalls: {
            type: "array",
            items: { type: "string" },
          },
        },
      },
    ],
    messages: {
      policyLiteral:
        "Policy literal '{{value}}' should usually be a named constant or enum value so the rule is searchable.",
    },
  },
  create(context) {
    const [{ allowedCalls = [] } = {}] = context.options;
    const callAllowlist = [...new Set([...DEFAULT_LITERAL_CALL_ALLOWLIST, ...allowedCalls])];

    function reportPolicyLiteral(node, value) {
      if (isTypeOnlyLiteral(node) || !literalLooksLikePolicy(value) || isAllowedLiteralContext(node, callAllowlist)) {
        return;
      }
      context.report({
        node,
        messageId: "policyLiteral",
        data: { value: String(value) },
      });
    }

    return {
      Literal(node) {
        if (!isStringOrNumberLiteral(node)) {
          return;
        }
        reportPolicyLiteral(node, node.value);
      },
      TemplateLiteral(node) {
        if (node.expressions.length > 0 || node.quasis.length !== 1) {
          return;
        }
        reportPolicyLiteral(node, node.quasis[0].value.cooked ?? node.quasis[0].value.raw);
      },
    };
  },
});

const noTrainWrecks = createRule({
  name: "/no-train-wrecks",
  meta: {
    type: "suggestion",
    docs: {
      description: "Flag deep property chains that expose transitive object structure.",
    },
    schema: [
      {
        type: "object",
        additionalProperties: false,
        properties: {
          maxDepth: { type: "integer", minimum: 1 },
        },
      },
    ],
    messages: {
      trainWreck: "Deep property chain exposes object internals; prefer a named query on the owning object.",
    },
  },
  create(context) {
    const [{ maxDepth = 3 } = {}] = context.options;

    return {
      MemberExpression(node) {
        if (
          isMemberDepthTooDeep(node, maxDepth) &&
          node.parent?.type !== "MemberExpression" &&
          node.parent?.type !== "OptionalMemberExpression"
        ) {
          context.report({ node, messageId: "trainWreck" });
        }
      },
      OptionalMemberExpression(node) {
        if (
          isMemberDepthTooDeep(node, maxDepth) &&
          node.parent?.type !== "MemberExpression" &&
          node.parent?.type !== "OptionalMemberExpression"
        ) {
          context.report({ node, messageId: "trainWreck" });
        }
      },
    };
  },
});

const rules = {
  "todo-format": todoFormat,
  "no-commented-out-code": noCommentedOutCode,
  "no-boolean-flag-arguments": noBooleanFlagArguments,
  "no-output-argument-mutation": noOutputArgumentMutation,
  "no-redundant-comment": noRedundantComment,
  "no-noisy-comments": noNoisyComments,
  "no-business-policy-literals": noBusinessPolicyLiterals,
  "no-train-wrecks": noTrainWrecks,
};

const plugin = {
  meta: {
    name: "eslint-plugin-clean-code",
    version: "0.1.0",
  },
  rules,
  configs: {
    recommended: {
      plugins: {
        "clean-code": undefined,
      },
      rules: {
        "clean-code/todo-format": "warn",
        "clean-code/no-commented-out-code": "warn",
        "clean-code/no-boolean-flag-arguments": "warn",
        "clean-code/no-output-argument-mutation": "warn",
        "clean-code/no-redundant-comment": "warn",
        "clean-code/no-noisy-comments": "warn",
        "clean-code/no-business-policy-literals": "warn",
        "clean-code/no-train-wrecks": "warn",
      },
    },
  },
};

plugin.configs.recommended.plugins["clean-code"] = plugin;

export default plugin;
export { rules };
