from rubigram.network.headers import CHROME_USER_AGENT, build_discovery_headers, build_rpc_headers


def test_rpc_headers_match_browser_profile():
    headers = build_rpc_headers()

    assert headers["user-agent"] == CHROME_USER_AGENT
    assert headers["content-type"] == "text/plain"
    assert headers["origin"] == "https://web.rubika.ir"
    assert headers["referer"] == "https://web.rubika.ir/"
    assert headers["sec-ch-ua-platform"] == '"Windows"'


def test_discovery_headers_match_browser_profile():
    headers = build_discovery_headers()

    assert headers["user-agent"] == CHROME_USER_AGENT
    assert headers["origin"] == "https://web.rubika.ir"
    assert headers["referer"] == "https://web.rubika.ir/"
    assert headers["sec-fetch-site"] == "cross-site"
