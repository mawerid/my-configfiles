"""GitLab MR mechanics for repository skills; standard library only.

No mutation occurs without an explicit capability. Transports are injectable
so offline checks never contact GitLab. CLI input/output is structured JSON.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import quote, urlencode, urlsplit


class Refused(ValueError):
    """An action cannot be justified by the supplied identity or evidence."""


class GlabTransport:
    def __init__(self, host):
        if not re.fullmatch(r"[A-Za-z0-9.-]+(?::[0-9]+)?", host):
            raise Refused("invalid GitLab host")
        self.host = host

    def request(self, method, path, payload=None, query=None):
        endpoint = path + ("?" + urlencode(query) if query else "")
        command = [
            "glab",
            "api",
            endpoint,
            "--hostname",
            self.host,
            "--method",
            method,
            "--include",
        ]
        if payload is not None:
            command += ["--header", "Content-Type: application/json", "--input", "-"]
        result = subprocess.run(
            command,
            input=json.dumps(payload) if payload is not None else None,
            text=True,
            capture_output=True,
            timeout=45,
            check=True,
        )
        # glab --include prints one response header block, followed by JSON.
        headers, separator, body = result.stdout.replace("\r\n", "\n").partition("\n\n")
        if not separator:
            raise Refused("missing API response headers")
        parsed = {}
        for line in headers.splitlines()[1:]:
            key, sep, value = line.partition(":")
            if sep:
                parsed[key.lower()] = value.strip()
        return json.loads(body) if body.strip() else None, parsed


def project_identity(remote):
    """Resolve an SSH/HTTPS origin to host and namespace/project, without auth."""
    if remote.startswith("git@"):
        host, sep, path = remote[4:].partition(":")
        if not sep:
            raise Refused("invalid SSH origin")
    else:
        url = urlsplit(remote)
        if (
            url.scheme != "https"
            or url.username
            or url.password
            or url.query
            or url.fragment
        ):
            raise Refused("expected an HTTPS or git@ origin without credentials")
        host, path = url.netloc, url.path.lstrip("/")
    path = path.removesuffix(".git")
    if not host or not re.fullmatch(r"[\w.-]+(?:/[\w.-]+)+", path):
        raise Refused("invalid origin project")
    return {"host": host, "path": path}


def diff_refs(mr):
    refs = mr.get("diff_refs") or {}
    if any(not refs.get(k) for k in ("base_sha", "start_sha", "head_sha")):
        raise Refused("MR diff refs not ready")
    if mr.get("sha") != refs["head_sha"]:
        raise Refused("inconsistent MR head")
    return {k: refs[k] for k in ("base_sha", "start_sha", "head_sha")}


def check_evidence(evidence, head):
    if not evidence or evidence.get("commit") != head:
        raise Refused("evidence must identify the checked commit")
    if not evidence.get("scope") or not evidence.get("checks"):
        raise Refused("evidence needs scope and actual checks/results")
    if any(not c.get("command") or not c.get("result") for c in evidence["checks"]):
        raise Refused("each check needs command and result")


def inline_position(refs, change, *, old_line=None, new_line=None):
    """Build a position only for a line present in this current text diff."""
    if change.get("too_large") or change.get("collapsed"):
        raise Refused("inline diff unavailable; use a general discussion")
    if old_line is None and new_line is None:
        raise Refused("inline position needs a line")
    old = new = None
    found = False
    for line in change.get("diff", "").splitlines():
        if line.startswith("@@"):
            match = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
            if match:
                old, new = map(int, match.groups())
            continue
        if old is None or line.startswith("\\"):
            continue
        pair = (
            (None, new)
            if line.startswith("+")
            else (old, None)
            if line.startswith("-")
            else (old, new)
        )
        if pair == (old_line, new_line):
            found = True
        if not line.startswith("+"):
            old += 1
        if not line.startswith("-"):
            new += 1
    if not found:
        raise Refused("line is absent from current diff or wrong side")
    result = {
        **refs,
        "position_type": "text",
        "old_path": change["old_path"],
        "new_path": change["new_path"],
    }
    if old_line is not None:
        result["old_line"] = old_line
    if new_line is not None:
        result["new_line"] = new_line
    return result


class GitLab:
    def __init__(self, transport, project, *, allowed=(), dry_run=True):
        if not isinstance(project, int) or project <= 0:
            raise Refused("use the verified numeric project ID")
        self.transport, self.project = transport, project
        self.allowed, self.dry_run = set(allowed), dry_run
        self.planned = []

    @property
    def root(self):
        return f"projects/{self.project}"

    def get(self, path, query=None):
        return self.transport.request("GET", path, query=query)[0]

    def pages(self, path, query=None):
        page, seen, result = "1", set(), []
        while page:
            if page in seen:
                raise Refused("pagination loop")
            seen.add(page)
            data, headers = self.transport.request(
                "GET", path, query={**(query or {}), "per_page": 100, "page": page}
            )
            if not isinstance(data, list):
                raise Refused("expected a paginated list")
            result.extend(data)
            page = headers.get("x-next-page", "")
        return result

    def mr(self, iid):
        if not isinstance(iid, int) or iid <= 0:
            raise Refused("invalid MR IID")
        mr = self.get(f"{self.root}/merge_requests/{iid}")
        if mr.get("project_id") != self.project or mr.get("iid") != iid:
            raise Refused("MR/project identity mismatch")
        return mr

    def snapshot(self, iid):
        mr = self.mr(iid)
        refs = diff_refs(mr)
        discussions = self.pages(f"{self.root}/merge_requests/{iid}/discussions")
        if diff_refs(self.mr(iid)) != refs:
            raise Refused("MR changed during inspection; restart")
        return {
            "project": self.project,
            "iid": iid,
            "mr": mr,
            "refs": refs,
            "discussions": discussions,
        }

    def current(self, snapshot, *, opened=True):
        if snapshot["project"] != self.project:
            raise Refused("snapshot belongs to another project")
        mr = self.mr(snapshot["iid"])
        if diff_refs(mr) != snapshot["refs"]:
            raise Refused("MR head/diff refs changed; inspect again")
        if opened and mr["state"] != "opened":
            raise Refused("MR is no longer open")
        return mr

    def _write(self, capability, method, path, payload):
        if capability not in self.allowed:
            raise Refused(f"not authorized: {capability}")
        action = {"method": method, "path": path, "payload": payload}
        self.planned.append(action)
        if self.dry_run:
            return {"dry_run": True, **action}
        # Never automatically retry a write: read remote state before recovery.
        return self.transport.request(method, path, payload=payload)[0]

    def post_note(
        self,
        snapshot,
        body,
        *,
        discussion=None,
        position=None,
        capability="post",
        plain=False,
    ):
        """Post a resolvable discussion, a reply, or (plain) a non-resolvable note."""
        if not body.strip():
            raise Refused("empty note")
        if capability not in {"post", "respond"}:
            raise Refused("invalid note capability")
        if discussion is not None and not any(
            d["id"] == discussion for d in snapshot["discussions"]
        ):
            raise Refused("unknown discussion ID")
        if plain and (discussion is not None or position is not None):
            raise Refused("a plain note has no thread or position")
        if position is not None and any(
            position.get(k) != v for k, v in snapshot["refs"].items()
        ):
            raise Refused("stale inline position")
        identity = json.dumps(
            [
                self.project,
                snapshot["iid"],
                snapshot["refs"],
                discussion,
                position,
                body,
            ],
            sort_keys=True,
        )
        marker = (
            "<!-- agent-mr:" + hashlib.sha256(identity.encode()).hexdigest() + " -->"
        )
        path = f"{self.root}/merge_requests/{snapshot['iid']}/discussions"
        # Check live state for writes that succeeded before a client timeout.
        for thread in self.pages(path):
            if any(marker in n.get("body", "") for n in thread["notes"]):
                return {"duplicate": True, "discussion": thread["id"]}
        self.current(snapshot)
        payload = {"body": body + "\n\n" + marker}
        if plain:
            # POST /notes makes a comment that is not resolvable, so it can
            # never block approval; /discussions threads always are.
            path = f"{self.root}/merge_requests/{snapshot['iid']}/notes"
        elif discussion:
            path += f"/{discussion}/notes"
        elif position:
            payload["position"] = position
        return self._write(capability, "POST", path, payload)

    def approve(self, snapshot, report, actor_id):
        """Approve only a current, independently reviewed head with complete evidence."""
        review_draft(snapshot, report)
        if any(f.get("blocking", True) for f in report["findings"]):
            raise Refused("blocking review findings remain")
        if any(
            r["status"] in {"still present", "question"} for r in report["rechecks"]
        ):
            raise Refused("unsettled original findings remain")
        mr = self.current(snapshot)
        if mr.get("author", {}).get("id") in {None, actor_id}:
            raise Refused("approval requires an independent reviewer")
        if mr.get("draft") or mr.get("work_in_progress"):
            raise Refused("draft MR cannot be approved")
        pipeline = mr.get("head_pipeline")
        if pipeline and (
            pipeline.get("sha") != snapshot["refs"]["head_sha"]
            or pipeline.get("status") != "success"
        ):
            raise Refused("current-head pipeline has not succeeded")
        path = f"{self.root}/merge_requests/{snapshot['iid']}"
        threads = self.pages(path + "/discussions")
        if any(
            n.get("resolvable") and not n.get("resolved")
            for t in threads
            for n in t["notes"]
        ):
            raise Refused("unresolved review discussions remain")
        approvals = self.get(path + "/approvals")
        if any(a["user"]["id"] == actor_id for a in approvals.get("approved_by", [])):
            return {"already_approved": True, "head": snapshot["refs"]["head_sha"]}
        self.current(snapshot)
        # GitLab binds this write atomically to the reviewed source SHA.
        return self._write(
            "approve", "POST", path + "/approve", {"sha": snapshot["refs"]["head_sha"]}
        )

    def resolve(self, snapshot, discussion, report):
        """Resolve a verified fixed finding only with the separate resolve capability."""
        review_draft(snapshot, report)
        item = next(
            (r for r in report["rechecks"] if r["discussion"] == discussion), None
        )
        if not item or item["status"] != "fixed":
            raise Refused("resolution requires a verified fixed finding")
        path = f"{self.root}/merge_requests/{snapshot['iid']}/discussions/{discussion}"
        thread = self.get(path)
        if thread.get("id") != discussion:
            raise Refused("unknown discussion ID")
        notes = [n for n in thread["notes"] if n.get("resolvable")]
        if not notes:
            raise Refused("discussion is not resolvable")
        if all(n.get("resolved") for n in notes):
            return {"already_resolved": True, "discussion": discussion}
        self.current(snapshot)
        return self._write("resolve", "PUT", path, {"resolved": True})

    def create_mr(self, source, head, title, description, *, target=None):
        """Reuse the exact open source/target MR, including after a lost response."""
        target = target or self.get(self.root)["default_branch"]
        if (
            not source
            or source == target
            or not title.strip()
            or not description.strip()
        ):
            raise Refused("expected a topic branch, title and reviewable description")
        path = f"{self.root}/merge_requests"
        existing = self.pages(
            path, {"state": "opened", "source_branch": source, "target_branch": target}
        )
        if len(existing) > 1:
            raise Refused("multiple matching MRs; select one explicitly")
        branch = self.get(f"{self.root}/repository/branches/{quote(source, safe='')}")
        if branch.get("commit", {}).get("id") != head:
            raise Refused("remote source branch differs from checked commit")
        payload = {"title": title, "description": description}
        if existing:
            snapshot = self.snapshot(existing[0]["iid"])
            mr = self.current(snapshot)
            if (
                mr["source_branch"] != source
                or mr["target_branch"] != target
                or mr["sha"] != head
            ):
                raise Refused("existing MR branch/head mismatch")
            if all(mr.get(k) == v for k, v in payload.items()):
                return {"reused": True, "iid": mr["iid"], "web_url": mr.get("web_url")}
            return self._write("create", "PUT", f"{path}/{mr['iid']}", payload)
        return self._write(
            "create",
            "POST",
            path,
            {**payload, "source_branch": source, "target_branch": target},
        )


class GitRepo:
    """Read checkout identity and push only an explicitly authorized topic head."""

    def __init__(self, path="."):
        self.path = path

    def git(self, *args):
        # Hooks export GIT_INDEX_FILE; -C alone does not isolate a worktree.
        env = os.environ.copy()
        for key in (
            "GIT_DIR",
            "GIT_WORK_TREE",
            "GIT_COMMON_DIR",
            "GIT_INDEX_FILE",
            "GIT_OBJECT_DIRECTORY",
            "GIT_ALTERNATE_OBJECT_DIRECTORIES",
            "GIT_PREFIX",
            "GIT_SHALLOW_FILE",
        ):
            env.pop(key, None)
        return subprocess.run(
            ["git", "-C", str(self.path), *args],
            env=env,
            text=True,
            capture_output=True,
            check=True,
            timeout=45,
        ).stdout.strip()

    def verify_origin(self, client, host):
        identity = project_identity(self.git("remote", "get-url", "origin"))
        project = client.get(client.root)
        if (
            identity != {"host": host, "path": project.get("path_with_namespace")}
            or project.get("id") != client.project
        ):
            raise Refused("checkout origin differs from verified GitLab project")
        if any(
            project_identity(url) != identity
            for url in self.git(
                "remote", "get-url", "--push", "--all", "origin"
            ).splitlines()
        ):
            raise Refused(
                "origin push destination differs from verified GitLab project"
            )

    @contextmanager
    def validation_checkout(self, head):
        """Validate committed files independently of the caller's local edits."""
        if not re.fullmatch(r"[0-9a-f]{40,64}", head):
            raise Refused("invalid validation commit SHA")
        if self.git("rev-parse", f"{head}^{{commit}}") != head:
            raise Refused("validation requires an exact commit")
        with tempfile.TemporaryDirectory(prefix="agent-validation-") as directory:
            path = Path(directory) / "checkout"
            self.git("worktree", "add", "--detach", str(path), head)
            try:
                yield GitRepo(path)
                if self.git(
                    "-C", str(path), "status", "--porcelain", "--untracked-files=all"
                ):
                    raise Refused(
                        "validation changed the committed checkout; fix and recheck"
                    )
            finally:
                self.git("worktree", "remove", "--force", str(path))

    @contextmanager
    def review_checkout(self, client, host, snapshot):
        """Yield an owned detached checkout; leave the caller's dirty tree untouched."""
        self.verify_origin(client, host)
        client.current(snapshot)
        head = snapshot["refs"]["head_sha"]
        if not re.fullmatch(r"[0-9a-f]{40,64}", head):
            raise Refused("invalid review commit SHA")
        self.git("fetch", "--no-tags", "origin", head)
        with tempfile.TemporaryDirectory(prefix="agent-review-") as directory:
            path = Path(directory) / "checkout"
            self.git("worktree", "add", "--detach", str(path), head)
            try:
                client.current(snapshot)
                yield GitRepo(path)
            finally:
                # Only this helper's disposable tree, never the caller's checkout.
                self.git("worktree", "remove", "--force", str(path))

    def verify(self, client, host, source, head):
        self.verify_origin(client, host)
        if (
            not source
            or source == client.get(client.root)["default_branch"]
            or source.startswith("-")
            or self.git("branch", "--show-current") != source
        ):
            raise Refused("checkout must be on the intended topic branch")
        if self.git("rev-parse", "HEAD") != head:
            raise Refused("local head changed since checks")

    def push(self, source, head, *, client, authorized=False, dry_run=True):
        if not authorized:
            raise Refused("topic push not authorized")
        if (
            not source
            or source == client.get(client.root)["default_branch"]
            or source.startswith("-")
            or self.git("branch", "--show-current") != source
            or self.git("rev-parse", "HEAD") != head
        ):
            raise Refused("topic/head changed before push")
        command = [
            "push",
            "--no-follow-tags",
            "origin",
            f"{head}:refs/heads/{source}",
        ]
        if dry_run:
            return {"dry_run": True, "git": command}
        self.git(*command)
        return {"pushed": head}


def author_reply(thread, author_id):
    """Return the latest author answer only if no later reviewer note exists."""
    notes = [n for n in thread["notes"] if not n.get("system")]
    if notes and notes[-1].get("author", {}).get("id") == author_id:
        return notes[-1]
    return None


def response_drafts(snapshot, dispositions, author_id, local_head, *, published=False):
    """Validate every disposition before any push/post and render honest replies."""
    threads = {
        t["id"]: t
        for t in snapshot["discussions"]
        if any(n.get("resolvable") for n in t["notes"])
    }
    if len({d["discussion"] for d in dispositions}) != len(dispositions):
        raise Refused("duplicate thread disposition")
    if set(threads) != {d["discussion"] for d in dispositions}:
        raise Refused("give one disposition for every review thread")
    drafts = []
    for item in dispositions:
        thread = threads[item["discussion"]]
        answer = author_reply(thread, author_id)
        if answer and not item.get("revisit"):
            drafts.append(
                {
                    "discussion": thread["id"],
                    "status": "already answered",
                    "note": answer["id"],
                }
            )
            continue
        status = item.get("status")
        if (
            status not in {"fixed", "disagree", "deferred", "question"}
            or not item.get("reason", "").strip()
        ):
            raise Refused("each response needs disposition and justified reason")
        check_evidence(item.get("evidence"), local_head)
        label = "Fixed" if status == "fixed" else status.capitalize()
        location = (
            f"in {local_head}"
            if published
            else f"locally at {local_head} (not published)"
        )
        checks = "; ".join(
            c["command"] + ": " + c["result"] for c in item["evidence"]["checks"]
        )
        body = f"{label} {location}. {item['reason']}\n\nEvidence ({item['evidence']['scope']}): {checks}"
        drafts.append(
            {
                "discussion": thread["id"],
                "status": status,
                "body": body,
                "evidence": item["evidence"],
            }
        )
    return drafts


def respond(
    client,
    snapshot,
    dispositions,
    author_id,
    local_head,
    *,
    publish=False,
    repo=None,
    host=None,
):
    drafts = response_drafts(snapshot, dispositions, author_id, local_head)
    if not publish or client.dry_run:
        return {"publication": "local draft; no push or replies", "drafts": drafts}
    if "respond" not in client.allowed:
        raise Refused("respond publication not authorized")
    current = client.current(snapshot)
    if current.get("author", {}).get("id") != author_id:
        raise Refused("respond requires the MR author identity")
    if all(d["status"] == "already answered" for d in drafts):
        return {"publication": "no new replies", "drafts": drafts}
    if repo is None:
        raise Refused("publication needs verified checkout")
    source = current["source_branch"]
    repo.verify(client, host, source, local_head)
    repo.push(source, local_head, client=client, authorized=True, dry_run=False)
    fresh = client.snapshot(snapshot["iid"])
    if fresh["refs"]["head_sha"] != local_head:
        raise Refused("pushed head not yet reflected in MR; inspect before resuming")
    # Re-read discussion state after pushing, including replies from other clients.
    drafts = response_drafts(fresh, dispositions, author_id, local_head, published=True)
    results = []
    for draft in drafts:
        if draft["status"] != "already answered":
            results.append(
                client.post_note(
                    fresh,
                    draft["body"],
                    discussion=draft["discussion"],
                    capability="respond",
                )
            )
    return {
        "publication": "pushed before replies",
        "drafts": drafts,
        "results": results,
    }


def review_draft(snapshot, report):
    """Validate initial/re-review coverage before any remote action."""
    head = snapshot["refs"]["head_sha"]
    check_evidence(report.get("evidence"), head)
    if report.get("refs") != snapshot["refs"]:
        raise Refused("review must record the current diff refs")
    previous = report.get("previous_head")
    if report.get("changes_reviewed") != {
        "base": previous or snapshot["refs"]["base_sha"],
        "head": head,
    }:
        raise Refused("review needs initial or intervening change coverage")
    threads = {
        t["id"]
        for t in snapshot["discussions"]
        if any(n.get("resolvable") for n in t["notes"])
    }
    rechecks = report.get("rechecks", [])
    if (
        len(rechecks) != len({r["discussion"] for r in rechecks})
        or {r["discussion"] for r in rechecks} != threads
    ):
        raise Refused("re-review must assess every original review thread")
    for item in rechecks:
        if (
            item.get("status") not in {"fixed", "still present", "disagree", "question"}
            or not item.get("reason", "").strip()
        ):
            raise Refused("recheck needs current-code disposition and evidence reason")
    if not report.get("summary", "").strip() or "findings" not in report:
        raise Refused("review needs a summary and explicit findings list")
    for finding in report["findings"]:
        if not finding.get("body", "").strip():
            raise Refused("empty review finding")
        position = finding.get("position")
        if position and any(position.get(k) != v for k, v in snapshot["refs"].items()):
            raise Refused("stale inline review position")
    checks = "; ".join(
        c["command"] + ": " + c["result"] for c in report["evidence"]["checks"]
    )
    recheck_text = "\n".join(
        f"{r['discussion']}: {r['status']}. {r['reason']}" for r in rechecks
    )
    return {
        "body": f"{report['summary']}\n\nReviewed {head}; scope: {report['evidence']['scope']}.\n{checks}\n{recheck_text}".rstrip(),
        "findings": report["findings"],
        "pipeline": snapshot["mr"].get("head_pipeline") or "absent",
    }


def review(client, snapshot, report, *, post=False):
    draft = review_draft(snapshot, report)
    client.current(snapshot)
    if not post:
        return {"draft": draft, "publication": "local draft"}
    results = [client.post_note(snapshot, draft["body"], plain=True)]
    for finding in draft["findings"]:
        results.append(
            client.post_note(
                snapshot, finding["body"], position=finding.get("position")
            )
        )
    return {"draft": draft, "results": results}


def release_acceptance(record):
    """Require successful, commit-bound offline/build and applicable external evidence."""
    head = record["head"]
    acceptance = record.get("acceptance", {})
    for name in ("offline", "build"):
        item = acceptance.get(name, {})
        check_evidence(item, head)
        if item.get("passed") is not True:
            raise Refused(f"release {name} acceptance has not passed")
    gpu = acceptance.get("external", {})
    if not isinstance(gpu.get("required"), bool) or not gpu.get("reason"):
        raise Refused("record whether external acceptance applies and why")
    if gpu["required"]:
        check_evidence(gpu, head)
        if gpu.get("passed") is not True:
            raise Refused("release external acceptance is still owed")


def release_commit(client, repo, record):
    """Verify the recorded release head landed by FF and remains on the default branch."""
    target = client.get(client.root)["default_branch"]
    mr = client.mr(record["iid"])
    head = record["head"]
    # GitLab can leave merge_commit_sha null for an FF merge.
    # The source SHA, fetched target ancestry and recorded contents still bind it.
    if (
        mr.get("state") != "merged"
        or mr.get("target_branch") != target
        or mr.get("source_project_id") != client.project
        or mr.get("sha") != head
        or mr.get("merge_commit_sha") not in (None, head)
        or mr.get("squash_commit_sha")
    ):
        raise Refused(
            "release MR is not the recorded fast-forward merge to the default branch"
        )
    pipeline = mr.get("head_pipeline")
    if pipeline and (
        pipeline.get("sha") != head or pipeline.get("status") != "success"
    ):
        raise Refused("release MR pipeline has not succeeded for the recorded head")
    repo.git("fetch", "--no-tags", "origin", f"refs/heads/{target}")
    target_head = repo.git("rev-parse", "FETCH_HEAD")
    if repo.git("merge-base", head, target_head) != head:
        raise Refused("release commit is not on fetched default branch")
    if repo.git("rev-parse", f"{head}^{{tree}}") != record["tree"]:
        raise Refused("landed content differs from recorded release tree")
    # The package has a static, literal SemVer. Fail closed on other syntax;
    # do not add a TOML dependency to the Python 3.10 offline environment.
    project = re.search(
        r"^\[project\]\s*\n(?:(?!^\[).)*",
        repo.git("show", f"{head}:pyproject.toml"),
        re.MULTILINE | re.DOTALL,
    )
    versions = re.findall(
        r"^version\s*=\s*(['\"])([0-9]+\.[0-9]+\.[0-9]+)\1\s*(?:#.*)?$",
        project[0] if project else "",
        re.MULTILINE,
    )
    version = record["version"]
    if len(versions) != 1 or versions[0][1] != version:
        raise Refused("landed package version differs from release record")
    changelog = repo.git("show", f"{head}:CHANGELOG.md")
    match = re.search(
        rf"^## \[{re.escape(version)}\] — \d{{4}}-\d{{2}}-\d{{2}}\n" r"(?:(?!^## ).)*",
        changelog,
        re.MULTILINE | re.DOTALL,
    )
    if not match or not re.search(r"^- \S", match[0], re.MULTILINE):
        raise Refused("landed changelog lacks the dated nonempty release section")
    return match[0].strip(), pipeline


def release_tags(repo, tag, head, message):
    """Inspect both tags; reject lightweight, retargeted or reannotated releases."""
    local = repo.git("for-each-ref", "--format=%(objectname)", f"refs/tags/{tag}")
    remote = repo.git("ls-remote", "--tags", "origin", f"refs/tags/{tag}")
    remote = remote.split()[0] if remote else ""
    if local and remote and local != remote:
        raise Refused("local and remote release tag objects conflict")
    for oid in set(filter(None, (local, remote))):
        if oid == remote:
            repo.git("fetch", "--no-tags", "origin", oid)
        if repo.git("cat-file", "-t", oid) != "tag":
            raise Refused("release tag must be annotated")
        headers, _, annotation = repo.git("cat-file", "tag", oid).partition("\n\n")
        if (
            f"object {head}" not in headers.splitlines()
            or "type commit" not in headers.splitlines()
            or f"tag {tag}" not in headers.splitlines()
            or annotation.strip() != message
        ):
            raise Refused(
                "existing release tag conflicts with landed content/changelog"
            )
    return local, remote


def release_publication(client, tag, head, version, package, job):
    """Report tag CI and registry files; inspection never retries upload jobs."""
    pipelines = client.pages(
        f"{client.root}/pipelines",
        {"ref": tag, "sha": head, "order_by": "id", "sort": "desc"},
    )
    pipelines = [p for p in pipelines if p.get("ref") == tag and p.get("sha") == head]
    if not pipelines:
        return {"status": "pipeline absent", "published": False}
    pipeline = max(pipelines, key=lambda p: p["id"])
    jobs = client.pages(f"{client.root}/pipelines/{pipeline['id']}/jobs")
    upload = [j for j in jobs if j.get("name") == job]
    result = {"pipeline": pipeline, "upload_jobs": upload, "published": False}
    if (
        pipeline.get("status") != "success"
        or not upload
        or any(j.get("status") != "success" for j in upload)
    ):
        return {**result, "status": "publication incomplete"}
    packages = client.pages(
        f"{client.root}/packages",
        {
            "package_type": "pypi",
            "package_name": package,
            "package_version": version,
        },
    )
    packages = [
        p
        for p in packages
        if p.get("name", "").replace("_", "-") == package.replace("_", "-")
        and p.get("version") == version
        and p.get("package_type") == "pypi"
        and p.get("status") == "default"
    ]
    filenames = [
        f["file_name"]
        for p in packages
        for f in client.pages(f"{client.root}/packages/{p['id']}/package_files")
    ]
    published = any(f.endswith(".whl") for f in filenames) and any(
        f.endswith(".tar.gz") for f in filenames
    )
    return {
        **result,
        "status": "published" if published else "registry artifacts missing",
        "published": published,
        "files": filenames,
    }


def release(client, repo, host, record, *, publish=False):
    """Continue a human-merged release; the only remote mutation is its tag push."""
    if not re.fullmatch(r"[0-9a-f]{40,64}", record["head"]) or not re.fullmatch(
        r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)", record["version"]
    ):
        raise Refused("invalid release version or commit")
    if record.get("human_merged") is not True:
        raise Refused("wait for the human to report the release MR merged")
    if publish and "release" not in client.allowed:
        raise Refused("release publication not authorized")
    repo.verify_origin(client, host)
    package = record["package_name"]
    job = record["publication_job"]
    if not package or not job:
        raise Refused("record the expected registry package and publication job")
    release_acceptance(record)
    message, pipeline = release_commit(client, repo, record)
    tag, head = f"v{record['version']}", record["head"]
    local, remote = release_tags(repo, tag, head, message)
    result = {"tag": tag, "head": head, "mr_pipeline": pipeline or "absent"}
    if not publish or client.dry_run:
        return {
            **result,
            "dry_run": True,
            "create_tag": not (local or remote),
            "push_tag": not remote,
        }
    if not remote:
        # Revalidate all mutable remote state immediately before each write.
        release_commit(client, repo, record)
        local, remote = release_tags(repo, tag, head, message)
        if not local and not remote:
            with tempfile.TemporaryDirectory(prefix="agent-release-") as directory:
                path = Path(directory) / "annotation"
                path.write_text(message + "\n")
                repo.git("tag", "-a", tag, head, "--cleanup=verbatim", "-F", str(path))
        if not remote:
            release_commit(client, repo, record)
            local, remote = release_tags(repo, tag, head, message)
            if not remote:
                if not local:
                    raise Refused("local release tag disappeared before push")
                repo.verify_origin(client, host)
                repo.git(
                    "push",
                    "--no-follow-tags",
                    "origin",
                    f"{local}:refs/tags/{tag}",
                )
    _, remote = release_tags(repo, tag, head, message)
    if not remote:
        raise Refused("release tag is not visible remotely; inspect before resuming")
    return {
        **result,
        "publication": release_publication(
            client, tag, head, record["version"], package, job
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "operation",
        choices=["inspect", "create", "respond", "review", "approve", "release"],
    )
    parser.add_argument(
        "--input", required=True, help="structured JSON; see adjacent mr-workflow.md"
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="authorize the selected skill action (review posts; approve approves)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="suppress every remote mutation, including push",
    )
    args = parser.parse_args()
    with open(args.input) as stream:
        data = json.load(stream)
    dry_run = args.dry_run or not args.publish
    allowed = (
        (("post",) if args.operation == "review" else (args.operation,))
        if args.publish
        else ()
    )
    client = GitLab(
        GlabTransport(data["host"]), data["project"], allowed=allowed, dry_run=dry_run
    )
    repo = GitRepo(data.get("repo", "."))
    if args.operation == "inspect":
        result = client.snapshot(data["iid"])
    elif args.operation == "release":
        result = release(
            client, repo, data["host"], data["release"], publish=args.publish
        )
    elif args.operation == "create":
        check_evidence(data.get("evidence"), data["head"])
        repo.verify(client, data["host"], data["source"], data["head"])
        if dry_run:
            result = {
                "dry_run": True,
                "source": data["source"],
                "head": data["head"],
                "title": data["title"],
                "description": data["description"],
                "push": repo.push(
                    data["source"], data["head"], client=client, authorized=True
                ),
            }
        else:
            repo.push(
                data["source"],
                data["head"],
                client=client,
                authorized=True,
                dry_run=False,
            )
            result = client.create_mr(
                data["source"], data["head"], data["title"], data["description"]
            )
    elif args.operation in {"review", "approve"}:
        snapshot = client.snapshot(data["iid"])
        if args.operation == "review":
            result = review(client, snapshot, data["report"], post=args.publish)
        else:
            actor = client.get("user")["id"]
            # Default CLI inspection is also a dry run; authorize no real approval.
            if not args.publish:
                client.allowed.add("approve")
            result = client.approve(snapshot, data["report"], actor)
    else:
        actor = client.get("user")["id"]
        result = respond(
            client,
            client.snapshot(data["iid"]),
            data["dispositions"],
            actor,
            data["head"],
            publish=args.publish,
            repo=repo,
            host=data["host"],
        )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
