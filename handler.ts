// Athletics Ireland RSS - Copyright Conor O'Neill 2022, conor@conoroneill.com
// LICENSE Apache-2.0

import { Handler } from 'aws-lambda';
import axios from 'axios';
import cheerio from 'cheerio';
import { Feed } from "feed";

export class AthleticsIrelandScraper {
    async scrapeNews(url: string) {

        const feed = new Feed({
            title: "Athletics Ireland News Feed",
            description: "RSS feed for Athletics Ireland website",
            id: "https://www.athleticsireland.ie/news",
            link: "https://www.athleticsireland.ie/news",
            language: "en", 
            image: "https://www.athleticsireland.ie/images/news/AI_Logo.jpg",
            favicon: "https://www.athleticsireland.ie/favicon.ico",
            copyright: "2022 © Athletics Ireland. All Rights Reserved.",
            updated: new Date(),
            generator: "AWS Lambda",
            feedLinks: {
              rss: "https://example.com/rss"
            },
            author: {
              name: "Athletics Ireland",
              email: "admin@athleticsireland.ie",
              link: "https://www.athleticsireland.ie/about/contact-us/meet-the-team"
            }
          });

        const response = await axios.get(url);
        const html = response.data;

        const $ = cheerio.load(html);
        $(".news-story").each(function() {
            let story = $(this).find("h3").first().find("a").first();
            let postLink = story.attr("href");
            let postText = story.text();
            let pubdate = $(this).find("span.date").first().text();
            let dateElements = pubdate.split(" / ");
            let publishDateTime = new Date(Number(dateElements[2]) + 2000, Number(dateElements[1])-1, Number(dateElements[0]));
            let imageURL =  $(this).find("img").attr("src");
            feed.addItem({
                title: postText,
                id: postLink,
                link: postLink || '',
                description: postText,
                content: '<img src="'+ imageURL + '"/><br>' + '<a href="'+ postLink + '">' + postText + "</a>",
                author: [
                  {
                    name: "Athletics Ireland",
                    email: "admin@athleticsireland.ie",
                    link: "https://www.athleticsireland.ie/about/contact-us/meet-the-team"
                  }
                ],
                date: publishDateTime,
                image: imageURL
              });

        });
        return(feed.rss2());
    }
}

export const rss: Handler = async (event: any) => {
  const scraper = new AthleticsIrelandScraper();
  let feed = await scraper.scrapeNews("https://www.athleticsireland.ie/news");
  const response = {
    statusCode: 200,
    headers: {
        'Content-Type': 'text/xml'
    },
    body: feed,
  };
  return(response);
}
